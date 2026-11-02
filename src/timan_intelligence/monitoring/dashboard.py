
"""Streamlit dashboard for monitoring TimanStat project implementation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from timan_intelligence.config import APP_NAME, APP_ORGANISATION
from timan_intelligence.monitoring.project_status import (
    build_project_status,
)


def _filter_features(
    features: list[dict],
    implementation_status: str,
    verification_status: str,
    search_text: str,
) -> list[dict]:
    """Filter feature records without modifying the original records."""

    filtered = features

    if implementation_status != "All":
        filtered = [
            feature
            for feature in filtered
            if feature["implementation_status"] == implementation_status
        ]

    if verification_status != "All":
        filtered = [
            feature
            for feature in filtered
            if feature["verification_status"] == verification_status
        ]

    search_text = search_text.strip().lower()

    if search_text:
        filtered = [
            feature
            for feature in filtered
            if search_text in " ".join(
                [
                    feature.get("feature_id", ""),
                    feature.get("name", ""),
                    feature.get("module", ""),
                    feature.get("description", ""),
                ]
            ).lower()
        ]

    return filtered


def render_project_status_dashboard() -> None:
    """Render the TimanStat implementation monitoring dashboard."""

    st.title("Project Implementation Dashboard")

    st.caption(
        f"{APP_NAME} | {APP_ORGANISATION} | "
        "Implementation and verification monitoring"
    )

    # Generate the report from the central feature registry.
    report = build_project_status()

    summary = report["summary"]
    implementation = report["implementation_status"]
    verification = report["verification_status"]
    features = report["features"]
    errors = report["registry_validation_errors"]

    st.markdown(
        "This dashboard reads directly from the central feature registry. "
        "Implementation status and verification maturity are reported "
        "separately."
    )

    st.caption(f"Report generated: {report['generated_at']}")

    # ---------------------------------------------------------
    # Key project indicators
    # ---------------------------------------------------------

    st.subheader("Project overview")

    metric_columns = st.columns(4)

    metric_columns[0].metric(
        "Total features",
        summary["total_features"],
    )

    metric_columns[1].metric(
        "Active features",
        summary["active_features"],
    )

    metric_columns[2].metric(
        "Implemented features",
        summary["implemented_features"],
    )

    metric_columns[3].metric(
        "Deprecated features",
        summary["deprecated_features"],
    )

    # ---------------------------------------------------------
    # Implementation and verification progress
    # ---------------------------------------------------------

    st.subheader("Implementation progress")

    implementation_rate = (
        summary["implementation_rate_percent"] / 100
    )

    st.progress(
        min(max(implementation_rate, 0.0), 1.0),
        text=(
            f"Implementation rate: "
            f"{summary['implementation_rate_percent']:.2f}%"
        ),
    )

    st.caption(
        "Calculated as implemented features divided by active features. "
        "Deprecated features are excluded."
    )

    st.subheader("Verification maturity")

    validation_rate = summary["validation_rate_percent"] / 100

    st.progress(
        min(max(validation_rate, 0.0), 1.0),
        text=(
            f"Validation rate: "
            f"{summary['validation_rate_percent']:.2f}%"
        ),
    )

    st.caption(
        "Calculated as validated features divided by implemented "
        "features. This is not the same as implementation progress."
    )

    verification_columns = st.columns(2)

    verification_columns[0].metric(
        "Validated features",
        summary["validated_features"],
    )

    verification_columns[1].metric(
        "Implemented, awaiting verification",
        summary["implemented_awaiting_verification"],
    )

    # ---------------------------------------------------------
    # Status distributions
    # ---------------------------------------------------------

    st.subheader("Implementation status distribution")

    implementation_frame = pd.DataFrame(
        [
            {"Status": status, "Features": count}
            for status, count in implementation.items()
        ]
    )

    if not implementation_frame.empty:
        st.bar_chart(
            implementation_frame.set_index("Status"),
            y="Features",
        )

    st.subheader("Verification status distribution")

    verification_frame = pd.DataFrame(
        [
            {"Status": status, "Features": count}
            for status, count in verification.items()
        ]
    )

    if not verification_frame.empty:
        st.bar_chart(
            verification_frame.set_index("Status"),
            y="Features",
        )

    # ---------------------------------------------------------
    # Outstanding work
    # ---------------------------------------------------------

    st.subheader("Outstanding implementation work")

    outstanding_implementation = [
        feature
        for feature in features
        if feature["implementation_status"] in (
            "planned",
            "in_development",
        )
    ]

    if outstanding_implementation:
        st.dataframe(
            pd.DataFrame(outstanding_implementation)[
                [
                    "feature_id",
                    "name",
                    "module",
                    "implementation_status",
                    "verification_status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No planned or in-development features are recorded.")

    st.subheader("Implemented features awaiting verification")

    awaiting_verification = [
        feature
        for feature in features
        if (
            feature["implementation_status"] == "implemented"
            and feature["verification_status"] != "validated"
        )
    ]

    if awaiting_verification:
        st.dataframe(
            pd.DataFrame(awaiting_verification)[
                [
                    "feature_id",
                    "name",
                    "module",
                    "verification_status",
                    "evidence",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No implemented features are currently awaiting validation."
        )

    # ---------------------------------------------------------
    # Complete feature register
    # ---------------------------------------------------------

    st.subheader("Feature register")

    if not features:
        st.warning("The feature registry currently contains no records.")
    else:
        implementation_options = [
            "All",
            *report["implementation_status"].keys(),
        ]

        verification_options = [
            "All",
            *report["verification_status"].keys(),
        ]

        filter_columns = st.columns(2)

        selected_implementation = filter_columns[0].selectbox(
            "Filter by implementation status",
            implementation_options,
        )

        selected_verification = filter_columns[1].selectbox(
            "Filter by verification status",
            verification_options,
        )

        search_text = st.text_input(
            "Search features",
            placeholder="Search by ID, name, module or description",
        )

        filtered_features = _filter_features(
            features=features,
            implementation_status=selected_implementation,
            verification_status=selected_verification,
            search_text=search_text,
        )

        st.caption(
            f"Showing {len(filtered_features)} of {len(features)} features."
        )

        if filtered_features:
            feature_frame = pd.DataFrame(filtered_features)

            st.dataframe(
                feature_frame[
                    [
                        "feature_id",
                        "name",
                        "module",
                        "implementation_status",
                        "verification_status",
                        "evidence",
                        "notes",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No features match the selected filters.")

    # ---------------------------------------------------------
    # Registry validation
    # ---------------------------------------------------------

    st.subheader("Registry validation")

    if errors:
        st.error(
            f"The registry reported {len(errors)} validation issue(s)."
        )

        for error in errors:
            st.write(f"- {error}")
    else:
        st.success("No registry validation errors were reported.")

    # ---------------------------------------------------------
    # Downloadable project status report
    # ---------------------------------------------------------

    st.subheader("Export project status")

    report_frame = pd.DataFrame(features)

    csv_data = report_frame.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download feature register (CSV)",
        data=csv_data,
        file_name="timanstat_feature_register.csv",
        mime="text/csv",
    )

    st.download_button(
        label="Download project status report (JSON)",
        data=__import__("json").dumps(
            report,
            indent=2,
            default=str,
        ).encode("utf-8"),
        file_name="timanstat_project_status.json",
        mime="application/json",
    )
