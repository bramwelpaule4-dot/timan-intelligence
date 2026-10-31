
"""Tests for the TimanStat method entity schema."""

import pytest

from timan_intelligence.registry.contracts import RegistryEntity
from timan_intelligence.registry.method import MethodEntity


def create_method(**overrides):
    """Create a valid method entity for testing."""
    values = {
        "entity_id": "method.inference.anova.one_way",
        "name": "One-way ANOVA",
        "description": (
            "A method for comparing the means of three or more "
            "independent groups."
        ),
        "knowledge_areas": ["frequentist_inference"],
        "statistical_purposes": ["inferential"],
        "use_cases": [
            "Compare the means of three or more independent groups."
        ],
        "data_requirements": [
            "A numeric outcome variable.",
            "A categorical grouping variable.",
        ],
        "statistical_specification": {
            "outcome_variable": "numeric",
            "group_variable": "categorical",
            "minimum_groups": 2,
        },
        "assumptions": [
            "Independent observations.",
            "Approximate normality within groups.",
            "Homogeneity of variances.",
        ],
        "estimands": ["Group population means"],
        "hypotheses": [
            "Null: all group population means are equal.",
            "Alternative: at least one group mean differs.",
        ],
        "outputs": [
            "F-statistic",
            "p-value",
            "degrees of freedom",
        ],
        "computational_requirements": [
            "At least two groups with valid numeric observations."
        ],
        "validation_requirements": [
            "Check outcome and grouping variables.",
            "Check group sizes and missing observations.",
        ],
        "limitations": [
            "Does not identify which groups differ without post-hoc analysis."
        ],
    }
    values.update(overrides)
    return MethodEntity(**values)


def test_method_entity_inherits_shared_registry_contract():
    method = create_method()

    assert isinstance(method, RegistryEntity)


def test_method_entity_has_method_entity_type():
    method = create_method()

    assert method.entity_type == "method"


def test_method_entity_preserves_canonical_identifier():
    method = create_method()

    assert method.entity_id == "method.inference.anova.one_way"


def test_method_entity_stores_use_cases():
    method = create_method()

    assert len(method.use_cases) == 1
    assert "independent groups" in method.use_cases[0]


def test_method_entity_stores_data_requirements():
    method = create_method()

    assert len(method.data_requirements) == 2
    assert "numeric outcome variable" in method.data_requirements[0]


def test_method_entity_stores_statistical_specification():
    method = create_method()

    assert method.statistical_specification["outcome_variable"] == "numeric"
    assert method.statistical_specification["group_variable"] == "categorical"


def test_method_entity_stores_assumptions():
    method = create_method()

    assert len(method.assumptions) == 3
    assert "Independent observations." in method.assumptions


def test_method_entity_stores_estimands_and_hypotheses():
    method = create_method()

    assert method.estimands == ["Group population means"]
    assert len(method.hypotheses) == 2


def test_method_entity_stores_outputs():
    method = create_method()

    assert "F-statistic" in method.outputs
    assert "p-value" in method.outputs


def test_method_entity_stores_computational_requirements():
    method = create_method()

    assert len(method.computational_requirements) == 1


def test_method_entity_stores_validation_requirements():
    method = create_method()

    assert len(method.validation_requirements) == 2


def test_method_entity_stores_limitations():
    method = create_method()

    assert len(method.limitations) == 1
    assert "post-hoc" in method.limitations[0]


def test_method_entity_has_independent_mutable_collections():
    first = create_method()
    second = create_method()

    first.use_cases.append("Additional use case")
    first.assumptions.append("Additional assumption")
    first.outputs.append("Additional output")

    assert "Additional use case" not in second.use_cases
    assert "Additional assumption" not in second.assumptions
    assert "Additional output" not in second.outputs


def test_method_entity_preserves_shared_lifecycle_fields():
    method = create_method(
        record_maturity="catalogued",
        implementation_status="implemented",
        verification_status="unit_tested",
    )

    assert method.record_maturity == "catalogued"
    assert method.implementation_status == "implemented"
    assert method.verification_status == "unit_tested"


def test_method_entity_preserves_shared_relationships():
    method = create_method()

    assert method.relationships == []
    assert method.related_entity_ids == []


def test_method_entity_requires_core_method_information():
    with pytest.raises(TypeError):
        MethodEntity(
            entity_id="method.inference.anova.one_way",
            name="One-way ANOVA",
            description="A method for comparing group means.",
            knowledge_areas=["frequentist_inference"],
            statistical_purposes=["inferential"],
        )
