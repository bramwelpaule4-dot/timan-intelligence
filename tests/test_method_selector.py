
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
