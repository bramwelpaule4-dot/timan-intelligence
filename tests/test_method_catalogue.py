"""Tests for the curated TimanStat statistical methods catalogue."""

import pytest

from timan_intelligence.registry.method_catalogue import (
    CATALOGUE_VERSION,
    IMPLEMENTED_METHODS,
    create_statistical_method_repository,
    get_statistical_method,
    get_statistical_method_summary,
    get_statistical_methods,
    validate_statistical_method_catalogue,
)


def test_catalogue_has_a_version_and_valid_records():
    assert CATALOGUE_VERSION == "1.0.0"
    assert validate_statistical_method_catalogue() == ()


def test_catalogue_registers_all_records_with_unique_canonical_ids():
    repository = create_statistical_method_repository()
    methods = repository.list_all()

    assert repository.count() == len(methods)
    assert len({method.entity_id for method in methods}) == len(methods)
    assert all(method.entity_id.startswith("method.") for method in methods)


def test_only_existing_execution_methods_are_marked_implemented():
    implemented = {
        method.entity_id
        for method in get_statistical_methods(
            implementation_status="implemented"
        )
    }

    assert implemented == IMPLEMENTED_METHODS
    assert len(implemented) == 45


def test_stl_decomposition_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.forecasting.time_series.stl_decomposition")
    assert method is not None
    assert method.name == "STL time-series decomposition"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_sarima_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.forecasting.time_series.sarima")
    assert method is not None
    assert method.name == "Seasonal ARIMA (SARIMA) time-series model"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_exact_binomial_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.comparison.binomial.one_sample")
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_planned_methods_are_not_marked_executable():
    planned = get_statistical_methods(implementation_status="planned")

    assert all(
        method.execution_eligibility == "not_assessed"
        for method in planned
    )
    assert all(
        method.verification_status == "not_tested"
        for method in planned
    )


def test_method_lookup_returns_expected_record():
    method = get_statistical_method(
        "method.inference.comparison.t_test.independent.welch"
    )

    assert method is not None
    assert method.name == "Welch's independent-samples t-test"
    assert method.implementation_status == "implemented"
    assert method.execution_eligibility == "conditional"


def test_paired_samples_t_test_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.comparison.t_test.paired")
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_chi_square_independence_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.association.chi_square.independence")
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_fisher_exact_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.association.fisher_exact")
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_unknown_method_lookup_returns_none():
    assert get_statistical_method("method.unknown.not_registered") is None


def test_catalogue_can_filter_by_family():
    methods = get_statistical_methods(method_family="correlation")

    assert {method.name for method in methods} == {
        "Pearson correlation",
        "Spearman rank correlation",
    }


def test_catalogue_can_filter_by_release_priority():
    methods = get_statistical_methods(release_priority="P1")

    assert methods
    assert all(
        method.metadata["release_priority"] == "P1"
        for method in methods
    )


def test_catalogue_filters_can_be_combined():
    methods = get_statistical_methods(
        implementation_status="implemented",
        method_family="group_comparison",
        release_priority="P1",
    )

    assert len(methods) == 8
    assert {method.name for method in methods} == {
        "Welch's independent-samples t-test",
        "One-way ANOVA",
        "Paired-samples t-test",
        "Two-independent-proportions comparison",
        "Wilcoxon signed-rank test",
        "Friedman test",
        "Pairwise Wilcoxon post-hoc test with Holm adjustment",
        "One-way repeated-measures ANOVA",
    }


def test_method_records_expose_requirements_and_validation_contracts():
    methods = get_statistical_methods()

    for method in methods:
        assert method.description.strip()
        assert method.method_families
        assert method.statistical_purposes
        assert method.data_requirements
        assert method.assumptions
        assert method.outputs
        assert method.validation_requirements
        assert method.statistical_specification["release_priority"] in {
            "P1", "P2", "P3"
        }


def test_survey_methods_explicitly_declare_sampling_design_requirements():
    weighted = get_statistical_method(
        "method.survey.estimation.weighted_proportion"
    )
    complex_design = get_statistical_method(
        "method.survey.inference.complex_design"
    )

    assert weighted is not None
    assert complex_design is not None
    assert "sampling_weight" in weighted.statistical_specification[
        "required_variable_roles"
    ]
    assert "design_identifier" in complex_design.statistical_specification[
        "required_variable_roles"
    ]
    assert weighted.implementation_status == "implemented"
    assert weighted.verification_status == "unit_tested"
    assert weighted.execution_eligibility == "conditional"
    assert weighted.statistical_specification["sampling_design_aware"] is True
    assert complex_design.implementation_status == "implemented"
    assert complex_design.verification_status == "unit_tested"
    assert complex_design.execution_eligibility == "conditional"
    assert complex_design.statistical_specification["sampling_design_aware"] is True


def test_catalogue_summary_reports_lifecycle_and_priorities():
    summary = get_statistical_method_summary()

    assert summary["catalogue_version"] == CATALOGUE_VERSION
    assert summary["total_methods"] == 45
    assert summary["implementation_status"]["implemented"] == 45
    assert summary["implementation_status"].get("planned", 0) == 0
    assert set(summary["release_priorities"]) == {"P1", "P2", "P3"}


def test_returned_method_records_do_not_mutate_catalogue_state():
    methods = get_statistical_methods()
    first_id = methods[0].entity_id
    methods[0].assumptions.append("External mutation")

    refreshed = get_statistical_method(first_id)

    assert refreshed is not None
    assert "External mutation" not in refreshed.assumptions


def test_repository_returns_defensive_copies():
    repository = create_statistical_method_repository()
    method = repository.list_all()[0]
    original_name = method.name
    method.name = "Mutated externally"

    stored = repository.get(method.entity_id)

    assert stored is not None
    assert stored.name == original_name


def test_welch_mean_difference_interval_is_registered_as_implemented():
    method = get_statistical_method(
        "method.inference.confidence_interval.mean_difference.welch"
    )
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.execution_eligibility == "conditional"


def test_paired_mean_change_interval_is_registered_as_implemented():
    method = get_statistical_method("method.inference.confidence_interval.mean_difference.paired")
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.execution_eligibility == "conditional"
    assert "paired" in method.statistical_specification["compatible_study_designs"]


def test_one_sample_t_test_is_registered_as_implemented():
    method = get_statistical_method(
        "method.inference.comparison.t_test.one_sample"
    )
    assert method is not None
    assert method.name == "One-sample Student's t-test"
    assert method.implementation_status == "implemented"
    assert method.execution_eligibility == "conditional"


def test_two_independent_proportions_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.comparison.proportions.independent")
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_two_proportions_confidence_interval_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.confidence_interval.proportions.independent")
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"



def test_mann_whitney_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.comparison.mann_whitney")
    assert method is not None
    assert method.name == "Mann–Whitney U test"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_kruskal_wallis_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.comparison.kruskal_wallis")
    assert method is not None
    assert method.name == "Kruskal–Wallis test"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_dunn_holm_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.comparison.posthoc.dunn_holm")
    assert method is not None
    assert method.name == "Dunn post-hoc test with Holm adjustment"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_wilcoxon_signed_rank_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.comparison.wilcoxon_signed_rank")
    assert method is not None
    assert method.name == "Wilcoxon signed-rank test"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_friedman_is_registered_for_repeated_measures():
    method = get_statistical_method("method.inference.comparison.friedman")
    assert method is not None
    assert method.name == "Friedman test"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"



def test_repeated_measures_anova_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.comparison.anova.repeated_measures")
    assert method is not None
    assert method.name == "One-way repeated-measures ANOVA"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"



def test_frequency_distribution_is_registered_as_executable():
    method = get_statistical_method("method.descriptive.categorical.frequency")
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "eligible"



def test_cross_tabulation_is_registered_as_executable():
    method = get_statistical_method("method.descriptive.categorical.cross_tabulation")
    assert method is not None
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "eligible"


def test_multiple_linear_regression_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.regression.linear.multiple")
    assert method is not None
    assert method.name == "Multiple linear regression"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_binary_logistic_regression_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.regression.logistic.binary")
    assert method is not None
    assert method.name == "Binary logistic regression"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_linear_simple_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.regression.linear.simple")
    assert method is not None
    assert method.name == "Simple linear regression"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_logistic_ordinal_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.regression.logistic.ordinal")
    assert method is not None
    assert method.name == "Ordinal logistic regression"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_logistic_multinomial_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.regression.logistic.multinomial")
    assert method is not None
    assert method.name == "Multinomial logistic regression"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_count_poisson_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.regression.count.poisson")
    assert method is not None
    assert method.name == "Poisson regression"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_count_negative_binomial_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.regression.count.negative_binomial")
    assert method is not None
    assert method.name == "Negative binomial regression"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_survival_kaplan_meier_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.survival.kaplan_meier")
    assert method is not None
    assert method.name == "Kaplan-Meier survival analysis"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"


def test_survival_cox_is_registered_as_conditionally_executable():
    method = get_statistical_method("method.inference.survival.cox")
    assert method is not None
    assert method.name == "Cox proportional hazards regression"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"
    assert method.execution_eligibility == "conditional"
