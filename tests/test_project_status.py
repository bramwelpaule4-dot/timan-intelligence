
"""Tests for the TimanStat project status reporting module."""

from timan_intelligence.monitoring.project_status import (
    _percentage,
    build_project_status,
)


def test_project_status_returns_expected_sections():
    report = build_project_status()

    expected_sections = {
        "generated_at",
        "summary",
        "implementation_status",
        "verification_status",
        "features",
        "registry_validation_errors",
    }

    assert expected_sections.issubset(report.keys())


def test_project_status_contains_a_generation_timestamp():
    report = build_project_status()

    assert isinstance(report["generated_at"], str)
    assert report["generated_at"]


def test_total_feature_count_matches_feature_records():
    report = build_project_status()

    assert (
        report["summary"]["total_features"]
        == len(report["features"])
    )


def test_implementation_counts_reconcile_with_total():
    report = build_project_status()

    implementation_total = sum(
        report["implementation_status"].values()
    )

    assert implementation_total == report["summary"]["total_features"]


def test_verification_counts_reconcile_with_total():
    report = build_project_status()

    verification_total = sum(
        report["verification_status"].values()
    )

    assert verification_total == report["summary"]["total_features"]


def test_active_and_deprecated_features_reconcile():
    report = build_project_status()
    summary = report["summary"]

    assert (
        summary["active_features"] + summary["deprecated_features"]
        == summary["total_features"]
    )


def test_implementation_rate_is_within_valid_range():
    report = build_project_status()

    rate = report["summary"]["implementation_rate_percent"]

    assert 0 <= rate <= 100


def test_validation_rate_is_within_valid_range():
    report = build_project_status()

    rate = report["summary"]["validation_rate_percent"]

    assert 0 <= rate <= 100


def test_implementation_rate_is_calculated_correctly():
    report = build_project_status()
    summary = report["summary"]

    expected = (
        round(
            summary["implemented_features"]
            / summary["active_features"] * 100,
            2,
        )
        if summary["active_features"]
        else 0.0
    )

    assert summary["implementation_rate_percent"] == expected


def test_validation_rate_is_calculated_correctly():
    report = build_project_status()
    summary = report["summary"]

    expected = (
        round(
            summary["validated_features"]
            / summary["implemented_features"] * 100,
            2,
        )
        if summary["implemented_features"]
        else 0.0
    )

    assert summary["validation_rate_percent"] == expected


def test_implemented_features_reconcile_with_validation_counts():
    report = build_project_status()
    summary = report["summary"]

    assert (
        summary["validated_features"]
        + summary["implemented_not_fully_validated"]
        == summary["implemented_features"]
    )


def test_implemented_not_fully_validated_count_is_correct():
    report = build_project_status()
    summary = report["summary"]

    expected = sum(
        1
        for feature in report["features"]
        if (
            feature["implementation_status"] == "implemented"
            and feature["verification_status"] != "validated"
        )
    )

    assert (
        summary["implemented_not_fully_validated"]
        == expected
    )


def test_percentage_handles_zero_denominator():
    assert _percentage(0, 0) == 0.0
    assert _percentage(5, 0) == 0.0


def test_percentage_calculates_expected_value():
    assert _percentage(4, 10) == 40.0
    assert _percentage(1, 3) == 33.33


def test_every_feature_record_contains_required_fields():
    report = build_project_status()

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


def test_feature_ids_are_unique_in_report():
    report = build_project_status()

    feature_ids = [
        feature["feature_id"]
        for feature in report["features"]
    ]

    assert len(feature_ids) == len(set(feature_ids))


def test_registry_validation_errors_are_exposed():
    report = build_project_status()

    assert isinstance(report["registry_validation_errors"], list)


def test_current_registry_has_no_validation_errors():
    report = build_project_status()

    assert report["registry_validation_errors"] == []
