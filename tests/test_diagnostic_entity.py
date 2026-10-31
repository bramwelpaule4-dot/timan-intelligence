
"""Tests for the Diagnostic Entity Schema."""

from datetime import datetime, timezone

from timan_intelligence.registry.contracts import RegistryEntity
from timan_intelligence.registry.diagnostic import DiagnosticEntity


def make_diagnostic(**overrides):
    """Create a diagnostic entity for testing."""
    data = {
        "entity_id": "diagnostic.normality.shapiro_wilk",
        "name": "Shapiro-Wilk Test",
        "description": (
            "A statistical test used to assess whether a sample "
            "is consistent with a normally distributed population."
        ),
        "knowledge_areas": ["statistical_diagnostics"],
        "statistical_purposes": ["inferential", "exploratory"],
        "diagnostic_category": "distribution",
        "diagnostic_type": "normality_test",
    }
    data.update(overrides)
    return DiagnosticEntity(**data)


def test_diagnostic_entity_is_a_registry_entity():
    diagnostic = make_diagnostic()

    assert isinstance(diagnostic, RegistryEntity)


def test_diagnostic_entity_has_correct_entity_type():
    diagnostic = make_diagnostic()

    assert diagnostic.entity_type == "diagnostic"


def test_diagnostic_entity_stores_canonical_identifier():
    diagnostic = make_diagnostic()

    assert diagnostic.entity_id == "diagnostic.normality.shapiro_wilk"


def test_diagnostic_entity_stores_diagnostic_category():
    diagnostic = make_diagnostic()

    assert diagnostic.diagnostic_category == "distribution"


def test_diagnostic_entity_stores_diagnostic_type():
    diagnostic = make_diagnostic()

    assert diagnostic.diagnostic_type == "normality_test"


def test_diagnostic_entity_supports_data_quality_diagnostics():
    diagnostic = make_diagnostic(
        entity_id="diagnostic.data_quality.missingness",
        name="Missing Data Assessment",
        diagnostic_category="data_quality",
        diagnostic_type="missingness",
    )

    assert diagnostic.diagnostic_category == "data_quality"
    assert diagnostic.diagnostic_type == "missingness"


def test_diagnostic_entity_supports_distribution_diagnostics():
    diagnostic = make_diagnostic(
        diagnostic_category="distribution",
        diagnostic_type="normality",
    )

    assert diagnostic.diagnostic_category == "distribution"
    assert diagnostic.diagnostic_type == "normality"


def test_diagnostic_entity_supports_assumption_diagnostics():
    diagnostic = make_diagnostic(
        entity_id="diagnostic.assumption.homoscedasticity",
        name="Homoscedasticity Assessment",
        diagnostic_category="assumption",
        diagnostic_type="equal_variance",
    )

    assert diagnostic.diagnostic_category == "assumption"


def test_diagnostic_entity_supports_model_adequacy_diagnostics():
    diagnostic = make_diagnostic(
        diagnostic_category="model_adequacy",
        diagnostic_type="goodness_of_fit",
    )

    assert diagnostic.diagnostic_category == "model_adequacy"


def test_diagnostic_entity_supports_residual_diagnostics():
    diagnostic = make_diagnostic(
        diagnostic_category="residual",
        diagnostic_type="residual_pattern",
    )

    assert diagnostic.diagnostic_category == "residual"


def test_diagnostic_entity_supports_influence_diagnostics():
    diagnostic = make_diagnostic(
        diagnostic_category="influence",
        diagnostic_type="influential_observation",
    )

    assert diagnostic.diagnostic_category == "influence"


def test_diagnostic_entity_supports_predictive_performance_diagnostics():
    diagnostic = make_diagnostic(
        diagnostic_category="predictive_performance",
        diagnostic_type="prediction_error",
    )

    assert diagnostic.diagnostic_category == "predictive_performance"


def test_diagnostic_entity_stores_purpose():
    diagnostic = make_diagnostic(
        purpose="Assess whether the normality assumption is reasonable."
    )

    assert "normality assumption" in diagnostic.purpose


def test_diagnostic_entity_stores_data_requirements():
    diagnostic = make_diagnostic(
        data_requirements=["At least three observations."]
    )

    assert diagnostic.data_requirements == [
        "At least three observations."
    ]


def test_diagnostic_entity_stores_applicable_variables():
    diagnostic = make_diagnostic(
        applicable_variables=["Outcome variable"]
    )

    assert diagnostic.applicable_variables == ["Outcome variable"]


def test_diagnostic_entity_stores_test_statistic():
    diagnostic = make_diagnostic(
        test_statistic={
            "name": "W",
            "description": "Shapiro-Wilk test statistic",
        }
    )

    assert diagnostic.test_statistic["name"] == "W"


def test_diagnostic_entity_stores_null_hypothesis():
    diagnostic = make_diagnostic(
        null_hypothesis="The observations come from a normal distribution."
    )

    assert "normal distribution" in diagnostic.null_hypothesis


def test_diagnostic_entity_stores_alternative_hypothesis():
    diagnostic = make_diagnostic(
        alternative_hypothesis=(
            "The observations do not come from a normal distribution."
        )
    )

    assert "do not come from a normal distribution" in (
        diagnostic.alternative_hypothesis
    )


def test_diagnostic_entity_can_identify_p_value_availability():
    diagnostic = make_diagnostic(
        produces_p_value=True
    )

    assert diagnostic.produces_p_value is True


def test_diagnostic_entity_can_represent_non_p_value_diagnostics():
    diagnostic = make_diagnostic(
        diagnostic_category="residual",
        diagnostic_type="residual_plot",
        produces_p_value=False,
    )

    assert diagnostic.produces_p_value is False


def test_diagnostic_entity_stores_threshold_information():
    diagnostic = make_diagnostic(
        thresholds={
            "alpha": 0.05,
            "interpretation": "Significance threshold",
        }
    )

    assert diagnostic.thresholds["alpha"] == 0.05


def test_diagnostic_entity_stores_interpretation_guidance():
    diagnostic = make_diagnostic(
        interpretation_guidance=[
            "A small p-value provides evidence against normality."
        ]
    )

    assert len(diagnostic.interpretation_guidance) == 1


def test_diagnostic_entity_stores_assumptions():
    diagnostic = make_diagnostic(
        assumptions=[
            "Observations are independent.",
            "The sample contains valid numerical observations.",
        ]
    )

    assert len(diagnostic.assumptions) == 2


def test_diagnostic_entity_stores_limitations():
    diagnostic = make_diagnostic(
        limitations=[
            "The test may have low power with small samples."
        ]
    )

    assert "low power" in diagnostic.limitations[0]


def test_diagnostic_entity_stores_recommended_actions():
    diagnostic = make_diagnostic(
        recommended_actions=[
            "Inspect a Q-Q plot alongside the test result."
        ]
    )

    assert len(diagnostic.recommended_actions) == 1


def test_diagnostic_entity_stores_applicable_model_ids():
    diagnostic = make_diagnostic(
        applicable_model_ids=[
            "model.regression.linear.multiple"
        ]
    )

    assert diagnostic.applicable_model_ids == [
        "model.regression.linear.multiple"
    ]


def test_diagnostic_entity_stores_applicable_method_ids():
    diagnostic = make_diagnostic(
        applicable_method_ids=[
            "method.inference.t_test.independent.welch"
        ]
    )

    assert diagnostic.applicable_method_ids == [
        "method.inference.t_test.independent.welch"
    ]


def test_diagnostic_entity_stores_related_diagnostic_ids():
    diagnostic = make_diagnostic(
        related_diagnostic_ids=[
            "diagnostic.distribution.qq_plot"
        ]
    )

    assert diagnostic.related_diagnostic_ids == [
        "diagnostic.distribution.qq_plot"
    ]


def test_diagnostic_entity_stores_output_fields():
    diagnostic = make_diagnostic(
        outputs=[
            "test_statistic",
            "p_value",
            "interpretation",
        ]
    )

    assert "p_value" in diagnostic.outputs


def test_diagnostic_entity_stores_visualization_ids():
    diagnostic = make_diagnostic(
        visualization_ids=[
            "visualization.distribution.qq_plot"
        ]
    )

    assert diagnostic.visualization_ids == [
        "visualization.distribution.qq_plot"
    ]


def test_diagnostic_entity_stores_references():
    diagnostic = make_diagnostic(
        diagnostic_references=[
            "Shapiro, S. S., & Wilk, M. B. (1965)."
        ]
    )

    assert len(diagnostic.diagnostic_references) == 1


def test_diagnostic_entity_default_collections_are_independent():
    first = make_diagnostic()
    second = make_diagnostic()

    first.outputs.append("p_value")

    assert second.outputs == []


def test_diagnostic_entity_preserves_shared_registry_fields():
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)

    diagnostic = make_diagnostic(
        aliases=["SW test"],
        application_domains=["general_research"],
        version="1.0.0",
        created_at=created,
    )

    assert diagnostic.aliases == ["SW test"]
    assert diagnostic.application_domains == ["general_research"]
    assert diagnostic.version == "1.0.0"
    assert diagnostic.created_at == created


def test_diagnostic_entity_has_default_collections():
    diagnostic = make_diagnostic()

    assert diagnostic.data_requirements == []
    assert diagnostic.applicable_variables == []
    assert diagnostic.interpretation_guidance == []
    assert diagnostic.assumptions == []
    assert diagnostic.limitations == []
    assert diagnostic.recommended_actions == []
    assert diagnostic.applicable_model_ids == []
    assert diagnostic.applicable_method_ids == []
    assert diagnostic.related_diagnostic_ids == []
    assert diagnostic.outputs == []
    assert diagnostic.visualization_ids == []
    assert diagnostic.diagnostic_references == []


def test_diagnostic_entity_has_default_test_statistic_and_thresholds():
    diagnostic = make_diagnostic()

    assert diagnostic.test_statistic == {}
    assert diagnostic.thresholds == {}


def test_diagnostic_entity_has_default_p_value_setting():
    diagnostic = make_diagnostic()

    assert diagnostic.produces_p_value is False


def test_diagnostic_entity_does_not_automatically_change_methods():
    diagnostic = make_diagnostic(
        recommended_actions=[
            "Review the normality assumption before selecting an alternative."
        ]
    )

    assert diagnostic.recommended_actions
    assert not hasattr(diagnostic, "automatically_switches_method")
