
"""Tests for the Measure Entity Schema."""

from datetime import datetime, timezone

from timan_intelligence.registry.contracts import RegistryEntity
from timan_intelligence.registry.measure import MeasureEntity


def make_measure(**overrides):
    """Create a measure entity for testing."""
    data = {
        "entity_id": "measure.effect.standardized_mean_difference.cohens_d",
        "name": "Cohen's d",
        "description": (
            "A standardized measure of the difference between two means."
        ),
        "knowledge_areas": ["effect_size_statistics"],
        "statistical_purposes": ["inferential", "descriptive"],
        "measure_category": "effect_size",
        "measure_type": "standardized_mean_difference",
    }
    data.update(overrides)
    return MeasureEntity(**data)


def test_measure_entity_is_a_registry_entity():
    measure = make_measure()

    assert isinstance(measure, RegistryEntity)


def test_measure_entity_has_correct_entity_type():
    measure = make_measure()

    assert measure.entity_type == "measure"


def test_measure_entity_stores_canonical_identifier():
    measure = make_measure()

    assert measure.entity_id == (
        "measure.effect.standardized_mean_difference.cohens_d"
    )


def test_measure_entity_stores_measure_category():
    measure = make_measure()

    assert measure.measure_category == "effect_size"


def test_measure_entity_stores_measure_type():
    measure = make_measure()

    assert measure.measure_type == "standardized_mean_difference"


def test_measure_entity_supports_descriptive_measures():
    measure = make_measure(
        entity_id="measure.descriptive.central_tendency.arithmetic_mean",
        name="Arithmetic Mean",
        measure_category="descriptive",
        measure_type="central_tendency",
    )

    assert measure.measure_category == "descriptive"
    assert measure.measure_type == "central_tendency"


def test_measure_entity_supports_distribution_measures():
    measure = make_measure(
        entity_id="measure.descriptive.distribution_shape.skewness",
        name="Skewness",
        measure_category="distribution",
        measure_type="distribution_shape",
    )

    assert measure.measure_category == "distribution"


def test_measure_entity_supports_effect_size_measures():
    measure = make_measure(
        measure_category="effect_size",
        measure_type="standardized_mean_difference",
    )

    assert measure.measure_category == "effect_size"


def test_measure_entity_supports_association_measures():
    measure = make_measure(
        entity_id="measure.association.correlation.pearson",
        name="Pearson Correlation Coefficient",
        measure_category="association",
        measure_type="correlation",
    )

    assert measure.measure_category == "association"


def test_measure_entity_supports_uncertainty_measures():
    measure = make_measure(
        entity_id="measure.uncertainty.standard_error",
        name="Standard Error",
        measure_category="uncertainty",
        measure_type="standard_error",
    )

    assert measure.measure_category == "uncertainty"


def test_measure_entity_supports_test_statistics():
    measure = make_measure(
        entity_id="measure.test_statistic.t_statistic",
        name="T Statistic",
        measure_category="test_statistic",
        measure_type="t_statistic",
    )

    assert measure.measure_category == "test_statistic"


def test_measure_entity_supports_model_performance_measures():
    measure = make_measure(
        entity_id="measure.model_performance.classification.accuracy",
        name="Classification Accuracy",
        measure_category="model_performance",
        measure_type="accuracy",
    )

    assert measure.measure_category == "model_performance"


def test_measure_entity_supports_population_parameter_estimates():
    measure = make_measure(
        entity_id="measure.parameter.population.mean",
        name="Population Mean Estimate",
        measure_category="population_parameter_estimate",
        measure_type="population_mean",
    )

    assert measure.measure_category == "population_parameter_estimate"


def test_measure_entity_stores_purpose():
    measure = make_measure(
        purpose="Quantify the standardized difference between two groups."
    )

    assert "standardized difference" in measure.purpose


def test_measure_entity_stores_mathematical_definition():
    measure = make_measure(
        mathematical_definition={
            "formula": "(mean_1 - mean_2) / pooled_standard_deviation",
            "notation": "d",
        }
    )

    assert measure.mathematical_definition["notation"] == "d"


def test_measure_entity_stores_formula_components():
    measure = make_measure(
        formula_components=[
            "mean_1",
            "mean_2",
            "pooled_standard_deviation",
        ]
    )

    assert len(measure.formula_components) == 3


def test_measure_entity_stores_measurement_scale():
    measure = make_measure(
        measurement_scale="continuous"
    )

    assert measure.measurement_scale == "continuous"


def test_measure_entity_stores_unit_of_measurement():
    measure = make_measure(
        unit="standard_deviations"
    )

    assert measure.unit == "standard_deviations"


def test_measure_entity_stores_valid_range():
    measure = make_measure(
        valid_range={
            "minimum": 0,
            "maximum": None,
            "minimum_inclusive": True,
        }
    )

    assert measure.valid_range["minimum"] == 0


def test_measure_entity_stores_interpretation_guidance():
    measure = make_measure(
        interpretation_guidance=[
            "Larger absolute values indicate greater standardized differences."
        ]
    )

    assert len(measure.interpretation_guidance) == 1


def test_measure_entity_stores_directionality():
    measure = make_measure(
        directionality="signed"
    )

    assert measure.directionality == "signed"


def test_measure_entity_stores_higher_is_better_information():
    measure = make_measure(
        higher_is_better=False
    )

    assert measure.higher_is_better is False


def test_measure_entity_stores_population_or_sample_scope():
    measure = make_measure(
        scope="sample"
    )

    assert measure.scope == "sample"


def test_measure_entity_stores_estimation_method_ids():
    measure = make_measure(
        estimation_method_ids=[
            "method.inference.t_test.independent.welch"
        ]
    )

    assert measure.estimation_method_ids == [
        "method.inference.t_test.independent.welch"
    ]


def test_measure_entity_stores_related_model_ids():
    measure = make_measure(
        related_model_ids=[
            "model.regression.linear.multiple"
        ]
    )

    assert measure.related_model_ids == [
        "model.regression.linear.multiple"
    ]


def test_measure_entity_stores_related_measure_ids():
    measure = make_measure(
        related_measure_ids=[
            "measure.uncertainty.standard_error"
        ]
    )

    assert measure.related_measure_ids == [
        "measure.uncertainty.standard_error"
    ]


def test_measure_entity_stores_visualization_ids():
    measure = make_measure(
        visualization_ids=[
            "visualization.effect_size.forest_plot"
        ]
    )

    assert measure.visualization_ids == [
        "visualization.effect_size.forest_plot"
    ]


def test_measure_entity_stores_limitations():
    measure = make_measure(
        limitations=[
            "Interpretation depends on the population and study context."
        ]
    )

    assert "population" in measure.limitations[0]


def test_measure_entity_stores_measure_references():
    measure = make_measure(
        measure_references=[
            "Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences."
        ]
    )

    assert len(measure.measure_references) == 1


def test_measure_entity_default_collections_are_independent():
    first = make_measure()
    second = make_measure()

    first.formula_components.append("additional_component")

    assert second.formula_components == []


def test_measure_entity_preserves_shared_registry_fields():
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)

    measure = make_measure(
        aliases=["Standardized mean difference"],
        application_domains=["general_research"],
        version="1.0.0",
        created_at=created,
    )

    assert measure.aliases == ["Standardized mean difference"]
    assert measure.application_domains == ["general_research"]
    assert measure.version == "1.0.0"
    assert measure.created_at == created


def test_measure_entity_has_default_collections():
    measure = make_measure()

    assert measure.formula_components == []
    assert measure.interpretation_guidance == []
    assert measure.estimation_method_ids == []
    assert measure.related_model_ids == []
    assert measure.related_measure_ids == []
    assert measure.visualization_ids == []
    assert measure.limitations == []
    assert measure.measure_references == []


def test_measure_entity_has_default_mathematical_definition():
    measure = make_measure()

    assert measure.mathematical_definition == {}


def test_measure_entity_has_default_valid_range():
    measure = make_measure()

    assert measure.valid_range == {}


def test_measure_entity_has_default_optional_measurement_fields():
    measure = make_measure()

    assert measure.measurement_scale is None
    assert measure.unit is None
    assert measure.directionality is None
    assert measure.higher_is_better is None
    assert measure.scope is None
