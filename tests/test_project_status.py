
from datetime import datetime

import pytest

from timan_intelligence.monitoring.project_status import (
    _percentage,
    build_project_status,
)
from timan_intelligence.registry.feature_registry import (
    get_all_features,
    validate_registry,
)


@pytest.fixture
def report():
    """Build a fresh project status report for each test."""
    return build_project_status()


def test_project_status_returns_dictionary(report):
    assert isinstance(report, dict)


def test_project_status_contains_required_sections(report):
    required_sections = {
        "generated_at",
        "summary",
        "implementation_status",
        "verification_status",
        "features",
        "registry_validation_errors",
    }

    assert required_sections.issubset(report.keys())


def test_generated_at_is_valid_datetime(report):
    generated_at = report["generated_at"]

    assert isinstance(generated_at, str)
    parsed_datetime = datetime.fromisoformat(generated_at)
    assert parsed_datetime is not None


def test_summary_contains_required_metrics(report):
    summary = report["summary"]

    required_metrics = {
        "total_features",
        "implemented_features",
        "in_development_features",
        "planned_features",
        "deprecated_features",
        "validated_features",
        "implemented_not_fully_validated",
        "implementation_rate_percent",
        "validation_rate_percent",
    }

    assert required_metrics.issubset(summary.keys())


def test_feature_records_match_registry(report):
    registry_features = get_all_features()

    assert len(report["features"]) == len(registry_features)


def test_total_features_matches_registry(report):
    summary = report["summary"]

    assert summary["total_features"] == len(get_all_features())


def test_implementation_status_counts_reconcile(report):
    summary = report["summary"]
    implementation_status = report["implementation_status"]

    assert (
        sum(implementation_status.values())
        == summary["total_features"]
    )


def test_verification_status_counts_reconcile(report):
    summary = report["summary"]
    verification_status = report["verification_status"]

    assert (
        sum(verification_status.values())
        == summary["total_features"]
    )


def test_implementation_status_counts_match_summary(report):
    summary = report["summary"]
    implementation_status = report["implementation_status"]

    assert (
        implementation_status["implemented"]
        == summary["implemented_features"]
    )

    assert (
        implementation_status["in_development"]
        == summary["in_development_features"]
    )

    assert (
        implementation_status["planned"]
        == summary["planned_features"]
    )

    assert (
        implementation_status["deprecated"]
        == summary["deprecated_features"]
    )


def test_implementation_counts_reconcile(report):
    summary = report["summary"]

    assert (
        summary["implemented_features"]
        + summary["in_development_features"]
        + summary["planned_features"]
        + summary["deprecated_features"]
        == summary["total_features"]
    )


def test_implemented_features_reconcile_with_validation_counts(report):
    summary = report["summary"]

    assert (
        summary["validated_features"]
        + summary["implemented_not_fully_validated"]
        == summary["implemented_features"]
    )


def test_validated_features_are_implemented(report):
    validated_features = [
        feature
        for feature in report["features"]
        if feature["verification_status"] == "validated"
    ]

    for feature in validated_features:
        assert feature["implementation_status"] == "implemented"


def test_implementation_rate_is_within_valid_range(report):
    rate = report["summary"]["implementation_rate_percent"]

    assert isinstance(rate, (int, float))
    assert 0 <= rate <= 100


def test_validation_rate_is_within_valid_range(report):
    rate = report["summary"]["validation_rate_percent"]

    assert isinstance(rate, (int, float))
    assert 0 <= rate <= 100


def test_implementation_rate_is_calculated_correctly(report):
    summary = report["summary"]

    active_features = (
        summary["total_features"] - summary["deprecated_features"]
    )

    if active_features == 0:
        expected_rate = 0.0
    else:
        expected_rate = round(
            summary["implemented_features"] / active_features * 100,
            2,
        )

    assert summary["implementation_rate_percent"] == expected_rate


def test_validation_rate_is_calculated_correctly(report):
    summary = report["summary"]

    implemented_features = summary["implemented_features"]

    if implemented_features == 0:
        expected_rate = 0.0
    else:
        expected_rate = round(
            summary["validated_features"]
            / implemented_features
            * 100,
            2,
        )

    assert summary["validation_rate_percent"] == expected_rate


def test_percentage_returns_zero_when_denominator_is_zero():
    assert _percentage(5, 0) == 0.0


def test_percentage_calculates_correctly():
    assert _percentage(25, 100) == 25.0


def test_percentage_rounds_to_two_decimal_places():
    assert _percentage(1, 3) == 33.33


def test_feature_records_contain_required_fields(report):
    required_fields = {
        "feature_id",
        "name",
        "module",
        "description",
        "implementation_status",
        "verification_status",
        "evidence",
        "notes",
    }

    for feature in report["features"]:
        assert required_fields.issubset(feature.keys())


def test_feature_ids_are_unique(report):
    feature_ids = [
        feature["feature_id"]
        for feature in report["features"]
    ]

    assert len(feature_ids) == len(set(feature_ids))


def test_feature_names_are_not_empty(report):
    for feature in report["features"]:
        assert isinstance(feature["name"], str)
        assert feature["name"].strip()


def test_feature_descriptions_are_not_empty(report):
    for feature in report["features"]:
        assert isinstance(feature["description"], str)
        assert feature["description"].strip()


def test_feature_modules_are_not_empty(report):
    for feature in report["features"]:
        assert isinstance(feature["module"], str)
        assert feature["module"].strip()


def test_feature_evidence_is_a_tuple_in_registry():
    for feature in get_all_features():
        assert isinstance(feature.evidence, tuple)


def test_registry_validation_returns_list():
    errors = validate_registry()

    assert isinstance(errors, list)


def test_registry_has_no_validation_errors(report):
    assert report["registry_validation_errors"] == []


def test_registry_validation_is_clean():
    assert validate_registry() == []


def test_report_features_have_valid_implementation_statuses(report):
    allowed_statuses = {
        "planned",
        "in_development",
        "implemented",
        "deprecated",
    }

    for feature in report["features"]:
        assert feature["implementation_status"] in allowed_statuses


def test_report_features_have_valid_verification_statuses(report):
    allowed_statuses = {
        "not_tested",
        "unit_tested",
        "integration_tested",
        "numerically_verified",
        "methodologically_reviewed",
        "validated",
    }

    for feature in report["features"]:
        assert feature["verification_status"] in allowed_statuses


def test_validated_status_requires_implemented_status(report):
    for feature in report["features"]:
        if feature["verification_status"] == "validated":
            assert feature["implementation_status"] == "implemented"


def test_implemented_not_fully_validated_is_non_negative(report):
    count = report["summary"]["implemented_not_fully_validated"]

    assert isinstance(count, int)
    assert count >= 0


def test_validated_features_count_matches_feature_records(report):
    expected_count = sum(
        1
        for feature in report["features"]
        if (
            feature["implementation_status"] == "implemented"
            and feature["verification_status"] == "validated"
        )
    )

    assert report["summary"]["validated_features"] == expected_count


def test_implemented_not_fully_validated_count_matches_feature_records(report):
    expected_count = sum(
        1
        for feature in report["features"]
        if (
            feature["implementation_status"] == "implemented"
            and feature["verification_status"] != "validated"
        )
    )

    assert (
        report["summary"]["implemented_not_fully_validated"]
        == expected_count
    )
