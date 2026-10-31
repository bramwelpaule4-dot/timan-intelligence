
"""Tests for the Theory Entity Schema."""

from dataclasses import fields

from timan_intelligence.registry.theory import TheoryEntity


def create_theory(**overrides):
    """Create a theory entity for testing."""
    data = {
        "entity_id": "theory.probability.central_limit_theorem",
        "name": "Central Limit Theorem",
        "description": (
            "Describes conditions under which standardised sums "
            "of random variables converge in distribution to a "
            "normal distribution."
        ),
        "knowledge_areas": ["probability_theory"],
        "statistical_purposes": ["foundational"],
    }
    data.update(overrides)
    return TheoryEntity(**data)


def test_theory_entity_can_be_created():
    entity = create_theory()

    assert entity.name == "Central Limit Theorem"
    assert entity.entity_type == "theory"


def test_theory_entity_inherits_shared_registry_fields():
    entity = create_theory()

    assert entity.entity_id == "theory.probability.central_limit_theorem"
    assert entity.description
    assert entity.knowledge_areas == ["probability_theory"]
    assert entity.statistical_purposes == ["foundational"]
    assert entity.record_maturity == "draft"


def test_entity_type_is_fixed_to_theory():
    entity = create_theory()

    assert entity.entity_type == "theory"


def test_entity_type_is_not_a_constructor_argument():
    entity_fields = {
        item.name: item
        for item in fields(TheoryEntity)
    }

    assert "entity_type" in entity_fields
    assert entity_fields["entity_type"].init is False


def test_default_theory_category_and_type():
    entity = create_theory()

    assert entity.theory_category == ""
    assert entity.theory_type == ""


def test_theory_definition_and_formal_statements():
    entity = create_theory(
        formal_definition={
            "statement": "A mathematical definition of the theorem."
        },
        propositions=[
            {"name": "Proposition 1", "statement": "A formal proposition."}
        ],
        theorems=[
            {"name": "Theorem 1", "statement": "A formal theorem."}
        ],
    )

    assert entity.formal_definition["statement"]
    assert entity.propositions[0]["name"] == "Proposition 1"
    assert entity.theorems[0]["name"] == "Theorem 1"


def test_assumptions_and_conditions_are_separate():
    entity = create_theory(
        assumptions=["Random variables are independent."],
        conditions=["The variables have finite variance."],
    )

    assert entity.assumptions
    assert entity.conditions


def test_mathematical_notation_and_proof_information():
    entity = create_theory(
        mathematical_notation={
            "expression": "X_n converges in distribution to N(0, 1)"
        },
        proof_information={
            "proof_status": "established",
            "proof_reference": "Standard probability theory text",
        },
    )

    assert entity.mathematical_notation["expression"]
    assert entity.proof_information["proof_status"] == "established"


def test_scope_and_applicability():
    entity = create_theory(
        scope=["Sums of independent random variables."],
        applicability=["Large-sample approximation."],
    )

    assert entity.scope
    assert entity.applicability


def test_related_theory_and_distribution_identifiers():
    entity = create_theory(
        related_theory_ids=["theory.probability.law_of_large_numbers"],
        related_distribution_ids=["distribution.continuous.normal"],
    )

    assert entity.related_theory_ids
    assert entity.related_distribution_ids


def test_related_method_and_model_identifiers():
    entity = create_theory(
        related_method_ids=["method.inference.z_test.one_sample"],
        related_model_ids=["model.regression.linear.multiple"],
    )

    assert entity.related_method_ids
    assert entity.related_model_ids


def test_implications_and_limitations():
    entity = create_theory(
        implications=["Supports normal approximations in inference."],
        limitations=["The theorem requires its stated convergence conditions."],
    )

    assert entity.implications
    assert entity.limitations


def test_theory_references():
    entity = create_theory(
        theory_references=["A recognised probability theory textbook."]
    )

    assert entity.theory_references


def test_theory_defaults_are_independent():
    first = create_theory()
    second = create_theory()

    first.propositions.append({"name": "Example"})
    first.assumptions.append("Example assumption.")

    assert second.propositions == []
    assert second.assumptions == []


def test_theory_default_collections():
    entity = create_theory()

    assert entity.formal_definition == {}
    assert entity.propositions == []
    assert entity.theorems == []
    assert entity.assumptions == []
    assert entity.conditions == []
    assert entity.mathematical_notation == {}
    assert entity.proof_information == {}
    assert entity.scope == []
    assert entity.applicability == []
    assert entity.related_theory_ids == []
    assert entity.related_distribution_ids == []
    assert entity.related_method_ids == []
    assert entity.related_model_ids == []
    assert entity.implications == []
    assert entity.limitations == []
    assert entity.theory_references == []
