
from timan_intelligence.core.method_selector import select_methods


def test_selects_descriptive_statistics_for_numeric_outcome():
    methods = select_methods(
        objective_type="description",
        outcome_type="numeric",
    )

    assert any(
        item.method == "Descriptive statistics"
        for item in methods
    )


def test_selects_categorical_descriptive_methods():
    methods = select_methods(
        objective_type="description",
        outcome_type="categorical",
    )

    assert any(
        item.method == "Frequencies and proportions"
        for item in methods
    )


def test_suggests_methods_for_two_independent_numeric_groups():
    methods = select_methods(
        objective_type="comparison",
        outcome_type="numeric",
        group_count=2,
        independent_groups=True,
    )

    names = {item.method for item in methods}

    assert "Independent-samples t-test" in names
    assert "Mann–Whitney U test" in names


def test_suggests_categorical_comparison_methods():
    methods = select_methods(
        objective_type="comparison",
        outcome_type="binary",
        group_count=2,
        independent_groups=True,
    )

    names = {item.method for item in methods}

    assert "Chi-square test of independence" in names
    assert "Fisher's exact test" in names


def test_suggests_correlation_for_two_numeric_variables():
    methods = select_methods(
        objective_type="association",
        outcome_type="numeric",
        predictor_type="numeric",
    )

    names = {item.method for item in methods}

    assert "Pearson correlation" in names
    assert "Spearman rank correlation" in names


def test_suggests_logistic_regression_for_binary_prediction():
    methods = select_methods(
        objective_type="prediction",
        outcome_type="binary",
    )

    assert any(
        item.method == "Logistic regression"
        for item in methods
    )


def test_suggests_linear_regression_for_numeric_prediction():
    methods = select_methods(
        objective_type="prediction",
        outcome_type="numeric",
    )

    assert any(
        item.method == "Linear regression"
        for item in methods
    )


def test_returns_no_methods_when_comparison_design_is_incomplete():
    methods = select_methods(
        objective_type="comparison",
        outcome_type="numeric",
    )

    assert methods == []


def test_candidates_require_review():
    methods = select_methods(
        objective_type="description",
        outcome_type="numeric",
    )

    assert methods
    assert all(
        item.status == "review_required"
        for item in methods
    )


def test_candidates_include_rationale_and_checks():
    methods = select_methods(
        objective_type="description",
        outcome_type="numeric",
    )

    assert methods

    for item in methods:
        assert item.rationale.strip()
        assert item.checks


def test_unknown_objective_is_not_silently_treated_as_valid():
    methods = select_methods(
        objective_type="unsupported_objective",
        outcome_type="numeric",
    )

    assert methods == []

from timan_intelligence.core.method_selector import (
    ELIGIBLE,
    CONDITIONALLY_ELIGIBLE,
    INSUFFICIENT_INFORMATION,
    INELIGIBLE,
    assess_preferred_method,
)


def test_preferred_method_requests_missing_group_information():
    result = assess_preferred_method(
        preferred_method="Independent-samples t-test",
        objective_type="comparison",
        outcome_type="numeric",
    )

    assert result.eligibility == INSUFFICIENT_INFORMATION
    assert result.clarification_questions
    assert result.alternatives == []


def test_preferred_method_identifies_incompatible_design():
    result = assess_preferred_method(
        preferred_method="Independent-samples t-test",
        objective_type="comparison",
        outcome_type="numeric",
        group_count=2,
        independent_groups=False,
    )

    assert result.eligibility == INELIGIBLE
    assert result.rationale
    assert result.alternatives == []


def test_preferred_method_can_be_conditionally_eligible():
    result = assess_preferred_method(
        preferred_method="Independent-samples t-test",
        objective_type="comparison",
        outcome_type="numeric",
        group_count=2,
        independent_groups=True,
    )

    assert result.eligibility == CONDITIONALLY_ELIGIBLE
    assert result.checks


def test_preferred_method_returns_alternatives_when_available():
    result = assess_preferred_method(
        preferred_method="Independent-samples t-test",
        objective_type="comparison",
        outcome_type="numeric",
        group_count=3,
        independent_groups=True,
    )

    assert result.eligibility == INELIGIBLE
    assert result.alternatives
    assert all(
        candidate.method != "Independent-samples t-test"
        for candidate in result.alternatives
    )


def test_unknown_preferred_method_requests_clarification():
    result = assess_preferred_method(
        preferred_method="Unknown statistical method",
        objective_type="description",
        outcome_type="numeric",
    )

    assert result.eligibility == INSUFFICIENT_INFORMATION
    assert result.clarification_questions


def test_assessment_discloses_unverified_assumptions():
    result = assess_preferred_method(
        preferred_method="Pearson correlation",
        objective_type="association",
        outcome_type="numeric",
        predictor_type="numeric",
    )

    assert result.eligibility == CONDITIONALLY_ELIGIBLE
    assert any(
        "assumptions" in check.lower()
        or "inspect" in check.lower()
        for check in result.checks
    )

def test_candidates_include_authoritative_catalogue_lifecycle_metadata():
    methods = select_methods(
        objective_type="comparison",
        outcome_type="numeric",
        group_count=2,
        independent_groups=True,
    )
    by_name = {item.method: item for item in methods}

    welch = by_name["Independent-samples t-test"]
    mann_whitney = by_name["Mann–Whitney U test"]

    assert welch.catalogue["method_id"] == (
        "method.inference.comparison.t_test.independent.welch"
    )
    assert welch.catalogue["implementation_status"] == "implemented"
    assert welch.catalogue["execution_eligibility"] == "conditional"
    assert mann_whitney.catalogue["implementation_status"] == "planned"
    assert mann_whitney.catalogue["execution_eligibility"] == "not_assessed"
    assert mann_whitney.catalogue["sampling_design_aware"] is False


def test_catalogued_method_without_assessment_rules_is_not_declared_eligible():
    result = assess_preferred_method(
        preferred_method="Confidence interval for a mean",
        objective_type="description",
        outcome_type="numeric",
    )

    assert result.eligibility == INSUFFICIENT_INFORMATION
    assert result.catalogue["method_id"] == (
        "method.inference.confidence_interval.mean"
    )
    assert "not yet been added" in result.rationale
