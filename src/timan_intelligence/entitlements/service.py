"""Server-side feature and usage enforcement for TimanStat."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from timan_intelligence.database.connection import database_connection, get_database_type
from timan_intelligence.entitlements.plans import EntitlementError, get_limit, has_feature
from timan_intelligence.entitlements.subscriptions import get_effective_plan_code


class FeatureAccessDenied(EntitlementError):
    """Raised when the effective plan does not include a feature."""


class UsageLimitExceeded(EntitlementError):
    """Raised when a usage request would exceed its plan allowance."""


USAGE_METRICS = frozenset({"monthly_analyses", "monthly_exports"})


def _placeholder() -> str:
    return "%s" if get_database_type() == "postgresql" else "?"


def _owner(user_id: str | None, organisation_id: str | None) -> tuple[str, str]:
    has_user = isinstance(user_id, str) and bool(user_id.strip())
    has_org = isinstance(organisation_id, str) and bool(organisation_id.strip())
    if has_user == has_org:
        raise EntitlementError("Provide exactly one usage owner.")
    return ("user_id", user_id.strip()) if has_user else ("organisation_id", organisation_id.strip())


def _period_start(value: date | str | None = None) -> date:
    if value is None:
        day = datetime.now(timezone.utc).date()
    elif isinstance(value, datetime):
        day = value.astimezone(timezone.utc).date()
    elif isinstance(value, date):
        day = value
    elif isinstance(value, str):
        try:
            day = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("Usage period must be an ISO date.") from exc
    else:
        raise ValueError("Usage period must be a date or ISO date string.")
    return day.replace(day=1)


def get_effective_entitlements(*, user_id: str, organisation_id: str | None = None) -> dict[str, Any]:
    from timan_intelligence.entitlements.plans import get_plan
    code = get_effective_plan_code(user_id=user_id, organisation_id=organisation_id)
    plan = get_plan(code)
    return {"plan_code": plan.code, "plan_name": plan.name, "features": plan.features, "limits": plan.limits}


class DatasetLimitExceeded(EntitlementError):
    """Raised when an uploaded dataset exceeds its plan allowance."""


def validate_dataset_limits(
    *, user_id: str, row_count: int | None = None,
    file_size_bytes: int | None = None, organisation_id: str | None = None,
) -> dict[str, int | None]:
    """Enforce plan upload-size and row limits before dataset use."""
    code = get_effective_plan_code(user_id=user_id, organisation_id=organisation_id)
    size_limit_mb = get_limit(code, "max_upload_size_mb")
    row_limit = get_limit(code, "max_dataset_rows")
    if file_size_bytes is not None:
        if isinstance(file_size_bytes, bool) or not isinstance(file_size_bytes, int) or file_size_bytes < 0:
            raise ValueError("File size must be a non-negative integer.")
        if size_limit_mb is not None and file_size_bytes > size_limit_mb * 1024 * 1024:
            raise DatasetLimitExceeded(
                f"The {code.title()} plan allows uploads up to {size_limit_mb} MB. "
                "Choose a smaller file or upgrade your plan."
            )
    if row_count is not None:
        if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 0:
            raise ValueError("Dataset row count must be a non-negative integer.")
        if row_limit is not None and row_count > row_limit:
            raise DatasetLimitExceeded(
                f"The {code.title()} plan allows datasets up to {row_limit:,} rows; "
                f"this dataset contains {row_count:,} rows. Upgrade your plan to import it."
            )
    return {"max_upload_size_mb": size_limit_mb, "max_dataset_rows": row_limit}


def require_feature(feature: str, *, user_id: str, organisation_id: str | None = None) -> str:
    code = get_effective_plan_code(user_id=user_id, organisation_id=organisation_id)
    if not has_feature(code, feature):
        raise FeatureAccessDenied(
            f"The '{feature}' feature is not included in the {code.title()} plan."
        )
    return code


def get_monthly_usage(
    metric: str, *, user_id: str | None = None,
    organisation_id: str | None = None, period_start: date | str | None = None,
) -> int:
    if metric not in USAGE_METRICS:
        raise EntitlementError("Unrecognised monthly usage metric.")
    column, owner_id = _owner(user_id, organisation_id)
    period = _period_start(period_start)
    p = _placeholder()
    with database_connection() as connection:
        row = connection.execute(
            f"SELECT usage_count FROM entitlement_usage WHERE {column} = {p} AND metric = {p} AND period_start = {p}",
            (owner_id, metric, period),
        ).fetchone()
    return int(row["usage_count"]) if row is not None else 0


def consume_monthly_usage(
    metric: str, *, user_id: str, organisation_id: str | None = None,
    amount: int = 1, period_start: date | str | None = None,
) -> int:
    """Atomically consume monthly quota; organisation usage is shared by members."""
    if metric not in USAGE_METRICS:
        raise EntitlementError("Unrecognised monthly usage metric.")
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        raise ValueError("Usage amount must be a positive integer.")

    # user_id identifies the actor; when organisation_id is supplied, that
    # organisation owns the counter and shares it across active members.
    column, owner_id = _owner(user_id if organisation_id is None else None, organisation_id)
    code = get_effective_plan_code(user_id=user_id, organisation_id=organisation_id)
    limit = get_limit(code, metric)
    if limit is not None and amount > limit:
        raise UsageLimitExceeded(
            f"The {code.title()} plan allows {limit} "
            f"{metric.replace('_', ' ')} per month; a single request "
            f"for {amount} would exceed that allowance."
        )
    period = _period_start(period_start)
    p = _placeholder()
    conflict = f"{column}, metric, period_start"
    record_id = str(uuid.uuid4())

    with database_connection() as connection:
        if limit is None:
            row = connection.execute(
                f"""
                INSERT INTO entitlement_usage (id, {column}, metric, period_start, usage_count)
                VALUES ({p}, {p}, {p}, {p}, {p})
                ON CONFLICT ({conflict}) DO UPDATE SET
                    usage_count = entitlement_usage.usage_count + excluded.usage_count,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING usage_count
                """,
                (record_id, owner_id, metric, period, amount),
            ).fetchone()
        else:
            row = connection.execute(
                f"""
                INSERT INTO entitlement_usage (id, {column}, metric, period_start, usage_count)
                VALUES ({p}, {p}, {p}, {p}, {p})
                ON CONFLICT ({conflict}) DO UPDATE SET
                    usage_count = entitlement_usage.usage_count + excluded.usage_count,
                    updated_at = CURRENT_TIMESTAMP
                WHERE entitlement_usage.usage_count + excluded.usage_count <= {p}
                RETURNING usage_count
                """,
                (record_id, owner_id, metric, period, amount, limit),
            ).fetchone()

    if row is None:
        current = get_monthly_usage(
            metric,
            user_id=user_id if column == "user_id" else None,
            organisation_id=organisation_id if column == "organisation_id" else None,
            period_start=period,
        )
        raise UsageLimitExceeded(
            f"The {code.title()} plan allows {limit} {metric.replace('_', ' ')} "
            f"per month; {current} have already been used."
        )
    return int(row["usage_count"])
