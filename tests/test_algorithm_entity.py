
"""Tests for the Algorithm Entity Schema."""

from datetime import datetime, timezone

from timan_intelligence.registry.contracts import RegistryEntity
from timan_intelligence.registry.algorithm import AlgorithmEntity


def make_algorithm(**overrides):
    """Create an algorithm entity for testing."""
    data = {
        "entity_id": "algorithm.resampling.bootstrap.nonparametric",
        "name": "Nonparametric Bootstrap",
        "description": (
            "A resampling algorithm that repeatedly draws samples "
            "with replacement from observed data."
        ),
        "knowledge_areas": ["resampling_statistics"],
        "statistical_purposes": ["inferential", "exploratory"],
        "algorithm_category": "resampling",
        "algorithm_type": "bootstrap",
    }
    data.update(overrides)
    return AlgorithmEntity(**data)


def test_algorithm_entity_is_a_registry_entity():
    algorithm = make_algorithm()

    assert isinstance(algorithm, RegistryEntity)


def test_algorithm_entity_has_correct_entity_type():
    algorithm = make_algorithm()

    assert algorithm.entity_type == "algorithm"


def test_algorithm_entity_stores_canonical_identifier():
    algorithm = make_algorithm()

    assert algorithm.entity_id == (
        "algorithm.resampling.bootstrap.nonparametric"
    )


def test_algorithm_entity_stores_algorithm_category():
    algorithm = make_algorithm()

    assert algorithm.algorithm_category == "resampling"


def test_algorithm_entity_stores_algorithm_type():
    algorithm = make_algorithm()

    assert algorithm.algorithm_type == "bootstrap"


def test_algorithm_entity_supports_simulation_algorithms():
    algorithm = make_algorithm(
        entity_id="algorithm.simulation.monte_carlo",
        name="Monte Carlo Simulation",
        algorithm_category="simulation",
        algorithm_type="monte_carlo",
    )

    assert algorithm.algorithm_category == "simulation"
    assert algorithm.algorithm_type == "monte_carlo"


def test_algorithm_entity_supports_bayesian_computation():
    algorithm = make_algorithm(
        entity_id="algorithm.bayesian_computation.mcmc.metropolis_hastings",
        name="Metropolis-Hastings",
        algorithm_category="bayesian_computation",
        algorithm_type="mcmc",
    )

    assert algorithm.algorithm_category == "bayesian_computation"
    assert algorithm.algorithm_type == "mcmc"


def test_algorithm_entity_supports_optimisation_algorithms():
    algorithm = make_algorithm(
        entity_id="algorithm.optimisation.gradient_descent",
        name="Gradient Descent",
        algorithm_category="optimisation",
        algorithm_type="gradient_descent",
    )

    assert algorithm.algorithm_category == "optimisation"


def test_algorithm_entity_supports_numerical_approximation():
    algorithm = make_algorithm(
        entity_id="algorithm.numerical_approximation.quadrature",
        name="Numerical Quadrature",
        algorithm_category="numerical_approximation",
        algorithm_type="quadrature",
    )

    assert algorithm.algorithm_category == "numerical_approximation"


def test_algorithm_entity_supports_matrix_computation():
    algorithm = make_algorithm(
        entity_id="algorithm.matrix_computation.decomposition.svd",
        name="Singular Value Decomposition",
        algorithm_category="matrix_computation",
        algorithm_type="matrix_decomposition",
    )

    assert algorithm.algorithm_category == "matrix_computation"


def test_algorithm_entity_supports_stochastic_computation():
    algorithm = make_algorithm(
        entity_id="algorithm.stochastic_computation.random_walk",
        name="Random Walk",
        algorithm_category="stochastic_computation",
        algorithm_type="random_walk",
    )

    assert algorithm.algorithm_category == "stochastic_computation"


def test_algorithm_entity_stores_purpose():
    algorithm = make_algorithm(
        purpose="Estimate sampling uncertainty through repeated resampling."
    )

    assert "sampling uncertainty" in algorithm.purpose


def test_algorithm_entity_stores_input_requirements():
    algorithm = make_algorithm(
        input_requirements=[
            "An observed dataset.",
            "A specified number of bootstrap replications.",
        ]
    )

    assert len(algorithm.input_requirements) == 2


def test_algorithm_entity_stores_output_specification():
    algorithm = make_algorithm(
        output_specification={
            "primary_output": "bootstrap_distribution",
            "additional_outputs": ["standard_error", "confidence_interval"],
        }
    )

    assert (
        algorithm.output_specification["primary_output"]
        == "bootstrap_distribution"
    )


def test_algorithm_entity_stores_parameters():
    algorithm = make_algorithm(
        parameters={
            "n_resamples": 2000,
            "confidence_level": 0.95,
        }
    )

    assert algorithm.parameters["n_resamples"] == 2000
    assert algorithm.parameters["confidence_level"] == 0.95


def test_algorithm_entity_stores_default_parameters():
    algorithm = make_algorithm(
        default_parameters={
            "n_resamples": 1000,
        }
    )

    assert algorithm.default_parameters["n_resamples"] == 1000


def test_algorithm_entity_stores_parameter_constraints():
    algorithm = make_algorithm(
        parameter_constraints={
            "n_resamples": {
                "minimum": 1,
                "type": "integer",
            }
        }
    )

    assert algorithm.parameter_constraints["n_resamples"]["minimum"] == 1


def test_algorithm_entity_stores_computational_complexity():
    algorithm = make_algorithm(
        computational_complexity={
            "time_complexity": "Depends on sample size and replications.",
            "space_complexity": "Depends on stored resamples.",
        }
    )

    assert "time_complexity" in algorithm.computational_complexity


def test_algorithm_entity_stores_convergence_requirements():
    algorithm = make_algorithm(
        convergence_requirements=[
            "Assess chain convergence using appropriate diagnostics."
        ]
    )

    assert len(algorithm.convergence_requirements) == 1


def test_algorithm_entity_stores_stopping_criteria():
    algorithm = make_algorithm(
        stopping_criteria=[
            "Stop when the maximum iteration count is reached."
        ]
    )

    assert len(algorithm.stopping_criteria) == 1


def test_algorithm_entity_stores_randomness_requirements():
    algorithm = make_algorithm(
        randomness_requirements={
            "requires_random_seed": True,
            "supports_reproducibility": True,
        }
    )

    assert algorithm.randomness_requirements["requires_random_seed"] is True


def test_algorithm_entity_stores_reproducibility_information():
    algorithm = make_algorithm(
        reproducibility={
            "seed_support": True,
            "deterministic_when_seeded": True,
        }
    )

    assert algorithm.reproducibility["seed_support"] is True


def test_algorithm_entity_stores_assumptions():
    algorithm = make_algorithm(
        assumptions=[
            "The observed sample adequately represents the population."
        ]
    )

    assert len(algorithm.assumptions) == 1


def test_algorithm_entity_stores_limitations():
    algorithm = make_algorithm(
        limitations=[
            "Bootstrap validity depends on the sampling structure."
        ]
    )

    assert "sampling structure" in algorithm.limitations[0]


def test_algorithm_entity_stores_validation_requirements():
    algorithm = make_algorithm(
        validation_requirements=[
            "Verify the resampling procedure against a known reference."
        ]
    )

    assert len(algorithm.validation_requirements) == 1


def test_algorithm_entity_stores_implementation_languages():
    algorithm = make_algorithm(
        implementation_languages=["Python", "R"]
    )

    assert algorithm.implementation_languages == ["Python", "R"]


def test_algorithm_entity_stores_software_dependencies():
    algorithm = make_algorithm(
        software_dependencies=["NumPy", "SciPy"]
    )

    assert algorithm.software_dependencies == ["NumPy", "SciPy"]


def test_algorithm_entity_stores_related_method_ids():
    algorithm = make_algorithm(
        related_method_ids=[
            "method.inference.bootstrap_confidence_interval"
        ]
    )

    assert algorithm.related_method_ids == [
        "method.inference.bootstrap_confidence_interval"
    ]


def test_algorithm_entity_stores_related_model_ids():
    algorithm = make_algorithm(
        related_model_ids=[
            "model.regression.linear.multiple"
        ]
    )

    assert algorithm.related_model_ids == [
        "model.regression.linear.multiple"
    ]


def test_algorithm_entity_stores_related_algorithm_ids():
    algorithm = make_algorithm(
        related_algorithm_ids=[
            "algorithm.resampling.bootstrap.parametric"
        ]
    )

    assert algorithm.related_algorithm_ids == [
        "algorithm.resampling.bootstrap.parametric"
    ]


def test_algorithm_entity_stores_references():
    algorithm = make_algorithm(
        algorithm_references=[
            "Efron, B. (1979). Bootstrap methods: Another look at the jackknife."
        ]
    )

    assert len(algorithm.algorithm_references) == 1


def test_algorithm_entity_default_collections_are_independent():
    first = make_algorithm()
    second = make_algorithm()

    first.input_requirements.append("Additional input")

    assert second.input_requirements == []


def test_algorithm_entity_preserves_shared_registry_fields():
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)

    algorithm = make_algorithm(
        aliases=["Bootstrap resampling"],
        application_domains=["general_research"],
        version="1.0.0",
        created_at=created,
    )

    assert algorithm.aliases == ["Bootstrap resampling"]
    assert algorithm.application_domains == ["general_research"]
    assert algorithm.version == "1.0.0"
    assert algorithm.created_at == created


def test_algorithm_entity_has_default_collections():
    algorithm = make_algorithm()

    assert algorithm.input_requirements == []
    assert algorithm.convergence_requirements == []
    assert algorithm.stopping_criteria == []
    assert algorithm.assumptions == []
    assert algorithm.limitations == []
    assert algorithm.validation_requirements == []
    assert algorithm.implementation_languages == []
    assert algorithm.software_dependencies == []
    assert algorithm.related_method_ids == []
    assert algorithm.related_model_ids == []
    assert algorithm.related_algorithm_ids == []
    assert algorithm.algorithm_references == []


def test_algorithm_entity_has_default_output_specification():
    algorithm = make_algorithm()

    assert algorithm.output_specification == {}


def test_algorithm_entity_has_default_parameter_collections():
    algorithm = make_algorithm()

    assert algorithm.parameters == {}
    assert algorithm.default_parameters == {}
    assert algorithm.parameter_constraints == {}


def test_algorithm_entity_has_default_computational_complexity():
    algorithm = make_algorithm()

    assert algorithm.computational_complexity == {}


def test_algorithm_entity_has_default_randomness_requirements():
    algorithm = make_algorithm()

    assert algorithm.randomness_requirements == {}


def test_algorithm_entity_has_default_reproducibility_information():
    algorithm = make_algorithm()

    assert algorithm.reproducibility == {}


def test_algorithm_entity_does_not_claim_to_be_a_statistical_method():
    algorithm = make_algorithm()

    assert algorithm.entity_type == "algorithm"
    assert not hasattr(algorithm, "method_family")
