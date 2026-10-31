
"""Tests for the Distribution Entity Schema."""

from dataclasses import fields

from timan_intelligence.registry.distribution import DistributionEntity


def create_distribution(**overrides):
    """Create a distribution entity for testing."""
    data = {
        "entity_id": "distribution.continuous.normal",
        "name": "Normal Distribution",
        "description": (
            "A continuous probability distribution defined by "
            "its location and scale parameters."
        ),
        "knowledge_areas": ["probability_theory"],
        "statistical_purposes": ["foundational"],
    }
    data.update(overrides)
    return DistributionEntity(**data)


def test_distribution_entity_can_be_created():
    entity = create_distribution()

    assert entity.name == "Normal Distribution"
    assert entity.entity_type == "distribution"


def test_distribution_entity_inherits_shared_registry_fields():
    entity = create_distribution()

    assert entity.entity_id == "distribution.continuous.normal"
    assert entity.description
    assert entity.knowledge_areas == ["probability_theory"]
    assert entity.statistical_purposes == ["foundational"]
    assert entity.record_maturity == "draft"


def test_entity_type_is_fixed_to_distribution():
    entity = create_distribution()

    assert entity.entity_type == "distribution"


def test_entity_type_is_not_a_constructor_argument():
    entity_fields = {
        item.name: item
        for item in fields(DistributionEntity)
    }

    assert "entity_type" in entity_fields
    assert entity_fields["entity_type"].init is False


def test_default_distribution_category_and_type():
    entity = create_distribution()

    assert entity.distribution_category == ""
    assert entity.distribution_type == ""


def test_distribution_family_and_dimension():
    entity = create_distribution(
        distribution_family="normal",
        dimension="univariate",
    )

    assert entity.distribution_family == "normal"
    assert entity.dimension == "univariate"


def test_probability_functions_are_separately_represented():
    entity = create_distribution(
        probability_functions={
            "pdf": "Probability density function",
            "cdf": "Cumulative distribution function",
            "quantile": "Inverse cumulative distribution function",
        }
    )

    assert "pdf" in entity.probability_functions
    assert "cdf" in entity.probability_functions
    assert "quantile" in entity.probability_functions


def test_probability_mass_function_is_supported():
    entity = create_distribution(
        probability_functions={
            "pmf": "Probability mass function",
        }
    )

    assert "pmf" in entity.probability_functions


def test_parameter_definitions_and_support():
    entity = create_distribution(
        parameters={
            "mean": {
                "symbol": "mu",
                "description": "Location parameter",
            },
            "standard_deviation": {
                "symbol": "sigma",
                "description": "Scale parameter",
            },
        },
        support={
            "type": "real",
            "lower_bound": float("-inf"),
            "upper_bound": float("inf"),
        },
    )

    assert entity.parameters["mean"]["symbol"] == "mu"
    assert entity.support["type"] == "real"


def test_moments_and_distribution_properties():
    entity = create_distribution(
        moments={
            "mean": "mu",
            "variance": "sigma squared",
        },
        properties=["symmetric", "unimodal"],
    )

    assert entity.moments["mean"] == "mu"
    assert "symmetric" in entity.properties


def test_characteristic_and_generating_functions():
    entity = create_distribution(
        characteristic_function={
            "expression": "Characteristic function representation"
        },
        generating_functions={
            "moment_generating_function": "MGF representation",
        },
    )

    assert entity.characteristic_function["expression"]
    assert "moment_generating_function" in entity.generating_functions


def test_sampling_and_simulation_information():
    entity = create_distribution(
        sampling_information={
            "algorithm": "inverse_transform",
            "requirements": ["uniform random numbers"],
        }
    )

    assert entity.sampling_information["algorithm"] == "inverse_transform"


def test_related_distribution_identifiers():
    entity = create_distribution(
        related_distribution_ids=[
            "distribution.continuous.student_t"
        ]
    )

    assert entity.related_distribution_ids


def test_related_theory_and_method_identifiers():
    entity = create_distribution(
        related_theory_ids=[
            "theory.probability.central_limit_theorem"
        ],
        related_method_ids=[
            "method.inference.t_test.independent.welch"
        ],
    )

    assert entity.related_theory_ids
    assert entity.related_method_ids


def test_applications_limitations_and_references():
    entity = create_distribution(
        applications=["Statistical modelling"],
        limitations=["Parameters must satisfy distribution constraints."],
        distribution_references=["Probability theory textbook"],
    )

    assert entity.applications
    assert entity.limitations
    assert entity.distribution_references


def test_distribution_defaults_are_independent():
    first = create_distribution()
    second = create_distribution()

    first.parameters["mean"] = {"symbol": "mu"}
    first.properties.append("symmetric")

    assert second.parameters == {}
    assert second.properties == []


def test_distribution_default_collections():
    entity = create_distribution()

    assert entity.parameters == {}
    assert entity.support == {}
    assert entity.probability_functions == {}
    assert entity.moments == {}
    assert entity.properties == []
    assert entity.characteristic_function == {}
    assert entity.generating_functions == {}
    assert entity.sampling_information == {}
    assert entity.related_distribution_ids == []
    assert entity.related_theory_ids == []
    assert entity.related_method_ids == []
    assert entity.applications == []
    assert entity.limitations == []
    assert entity.distribution_references == []
