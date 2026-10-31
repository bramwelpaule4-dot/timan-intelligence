
"""Tests for the Design Entity Schema."""

from datetime import datetime, timezone

import pytest

from timan_intelligence.registry.design import DesignEntity
from timan_intelligence.registry.contracts import RegistryEntity


def make_design(**overrides):
    """Create a valid design entity for testing."""
    data = {
        "entity_id": "design.experiment.randomized_complete_block",
        "name": "Randomized Complete Block Design",
        "description": (
            "An experimental design in which experimental units "
            "are grouped into blocks and treatments are randomized "
            "within each block."
        ),
        "knowledge_areas": ["experimental_design"],
        "statistical_purposes": ["causal"],
        "design_category": "experimental",
        "design_type": "randomized_complete_block",
    }
    data.update(overrides)
    return DesignEntity(**data)


def test_design_entity_is_a_registry_entity():
    design = make_design()

    assert isinstance(design, RegistryEntity)


def test_design_entity_has_correct_entity_type():
    design = make_design()

    assert design.entity_type == "design"


def test_design_entity_has_canonical_identifier():
    design = make_design()

    assert design.entity_id == (
        "design.experiment.randomized_complete_block"
    )


def test_design_entity_stores_design_category():
    design = make_design()

    assert design.design_category == "experimental"


def test_design_entity_stores_design_type():
    design = make_design()

    assert design.design_type == "randomized_complete_block"


def test_design_entity_supports_observational_designs():
    design = make_design(
        entity_id="design.observational.cohort.prospective",
        name="Prospective Cohort Design",
        design_category="observational",
        design_type="prospective_cohort",
    )

    assert design.design_category == "observational"
    assert design.design_type == "prospective_cohort"


def test_design_entity_supports_sampling_designs():
    design = make_design(
        entity_id="design.sampling.probability.stratified",
        name="Stratified Sampling Design",
        design_category="sampling",
        design_type="stratified_sampling",
    )

    assert design.design_category == "sampling"
    assert design.design_type == "stratified_sampling"


def test_design_entity_stores_sampling_unit():
    design = make_design(
        sampling_unit="Household"
    )

    assert design.sampling_unit == "Household"


def test_design_entity_stores_allocation_unit():
    design = make_design(
        allocation_unit="Village"
    )

    assert design.allocation_unit == "Village"


def test_design_entity_stores_observation_unit():
    design = make_design(
        observation_unit="Individual"
    )

    assert design.observation_unit == "Individual"


def test_design_entity_stores_analysis_unit():
    design = make_design(
        analysis_unit="Household"
    )

    assert design.analysis_unit == "Household"


def test_design_entity_distinguishes_study_units():
    design = make_design(
        sampling_unit="Household",
        allocation_unit="Village",
        observation_unit="Individual",
        analysis_unit="Household",
    )

    assert design.sampling_unit == "Household"
    assert design.allocation_unit == "Village"
    assert design.observation_unit == "Individual"
    assert design.analysis_unit == "Household"


def test_design_entity_stores_randomization_method():
    design = make_design(
        randomization_method="Computer-generated random allocation"
    )

    assert design.randomization_method == (
        "Computer-generated random allocation"
    )


def test_design_entity_stores_sampling_method():
    design = make_design(
        sampling_method="Multistage cluster sampling"
    )

    assert design.sampling_method == "Multistage cluster sampling"


def test_design_entity_stores_control_group_information():
    design = make_design(
        control_group={
            "present": True,
            "type": "usual_care",
        }
    )

    assert design.control_group["present"] is True
    assert design.control_group["type"] == "usual_care"


def test_design_entity_stores_treatment_arms():
    design = make_design(
        treatment_arms=[
            {"name": "Intervention"},
            {"name": "Control"},
        ]
    )

    assert len(design.treatment_arms) == 2
    assert design.treatment_arms[0]["name"] == "Intervention"


def test_design_entity_stores_blinding_information():
    design = make_design(
        blinding={
            "type": "double_blind",
            "details": "Participants and outcome assessors are blinded.",
        }
    )

    assert design.blinding["type"] == "double_blind"


def test_design_entity_stores_repeated_measurement_information():
    design = make_design(
        repeated_measures=True,
        measurement_occasions=["Baseline", "Midline", "Endline"],
    )

    assert design.repeated_measures is True
    assert design.measurement_occasions == [
        "Baseline",
        "Midline",
        "Endline",
    ]


def test_design_entity_stores_cluster_information():
    design = make_design(
        clustering={
            "clustered": True,
            "cluster_unit": "Village",
        }
    )

    assert design.clustering["clustered"] is True
    assert design.clustering["cluster_unit"] == "Village"


def test_design_entity_stores_stratification_variables():
    design = make_design(
        stratification_variables=["Gender", "County"]
    )

    assert design.stratification_variables == ["Gender", "County"]


def test_design_entity_stores_design_structure():
    design = make_design(
        design_structure={
            "blocks": 5,
            "treatments_per_block": 3,
        }
    )

    assert design.design_structure["blocks"] == 5
    assert design.design_structure["treatments_per_block"] == 3


def test_design_entity_stores_assumptions():
    design = make_design(
        assumptions=[
            "Experimental units are independent.",
            "Treatment allocation is random within blocks.",
        ]
    )

    assert len(design.assumptions) == 2


def test_design_entity_stores_strengths():
    design = make_design(
        strengths=["Controls variation between blocks."]
    )

    assert design.strengths == [
        "Controls variation between blocks."
    ]


def test_design_entity_stores_limitations():
    design = make_design(
        limitations=["Results may not generalize beyond the study population."]
    )

    assert "generalize" in design.limitations[0].lower()


def test_design_entity_stores_analysis_implications():
    design = make_design(
        analysis_implications=[
            "Account for blocking in the statistical analysis."
        ]
    )

    assert design.analysis_implications == [
        "Account for blocking in the statistical analysis."
    ]


def test_design_entity_stores_related_methods():
    design = make_design(
        related_method_ids=[
            "method.inference.anova.one_way"
        ]
    )

    assert design.related_method_ids == [
        "method.inference.anova.one_way"
    ]


def test_design_entity_stores_related_model_ids():
    design = make_design(
        related_model_ids=[
            "model.regression.linear.multiple"
        ]
    )

    assert design.related_model_ids == [
        "model.regression.linear.multiple"
    ]


def test_design_entity_stores_design_references():
    design = make_design(
        design_references=[
            "Fisher, R. A. (1935). The Design of Experiments."
        ]
    )

    assert len(design.design_references) == 1


def test_design_entity_default_collections_are_independent():
    first = make_design()
    second = make_design()

    first.treatment_arms.append({"name": "Intervention"})

    assert second.treatment_arms == []


def test_design_entity_preserves_shared_registry_fields():
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)

    design = make_design(
        aliases=["RCBD"],
        application_domains=["agriculture"],
        version="1.0.0",
        created_at=created,
    )

    assert design.aliases == ["RCBD"]
    assert design.application_domains == ["agriculture"]
    assert design.version == "1.0.0"
    assert design.created_at == created


def test_design_entity_has_default_design_collections():
    design = make_design()

    assert design.treatment_arms == []
    assert design.measurement_occasions == []
    assert design.stratification_variables == []
    assert design.assumptions == []
    assert design.strengths == []
    assert design.limitations == []
    assert design.analysis_implications == []
    assert design.related_method_ids == []
    assert design.related_model_ids == []
    assert design.design_references == []


def test_design_entity_has_default_optional_unit_fields():
    design = make_design()

    assert design.sampling_unit is None
    assert design.allocation_unit is None
    assert design.observation_unit is None
    assert design.analysis_unit is None


def test_design_entity_has_default_randomization_and_sampling_fields():
    design = make_design()

    assert design.randomization_method is None
    assert design.sampling_method is None


def test_design_entity_has_default_control_and_blinding_information():
    design = make_design()

    assert design.control_group == {}
    assert design.blinding == {}


def test_design_entity_has_default_repeated_measurement_setting():
    design = make_design()

    assert design.repeated_measures is False


def test_design_entity_has_default_clustering_information():
    design = make_design()

    assert design.clustering == {}


def test_design_entity_has_default_design_structure():
    design = make_design()

    assert design.design_structure == {}
