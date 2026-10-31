"""Tests for TimanStat's canonical statistical registry identifiers."""

import pytest

from timan_intelligence.registry.identifiers import (
    IdentifierValidationError,
    validate_entity_id,
)


@pytest.mark.parametrize(
    "entity_id",
    [
        "method.inference.t_test.independent.welch",
        "method.inference.anova.one_way",
        "model.regression.linear.multiple",
        "design.experiment.randomized_complete_block",
        "diagnostic.normality.shapiro_wilk",
        "algorithm.resampling.bootstrap.nonparametric",
        "measure.effect.cohens_d",
        "visualization.distribution.histogram",
        "theory.probability.central_limit_theorem",
        "distribution.probability.normal",
    ],
)
def test_accepts_valid_canonical_identifiers(entity_id):
    """Valid identifiers from all nine entity types are accepted."""
    assert validate_entity_id(entity_id) == entity_id


@pytest.mark.parametrize(
    "entity_id",
    [
        "",
        "Method.inference.anova.one_way",
        "method",
        "method.",
        ".method.inference.anova",
        "method..anova.one_way",
        "method.inference.one way",
        "method.inference.anova/one_way",
        "unknown.inference.anova.one_way",
        "method.inference.anova.one_way.",
    ],
)
def test_rejects_invalid_canonical_identifiers(entity_id):
    """Malformed identifiers are rejected explicitly."""
    with pytest.raises(IdentifierValidationError):
        validate_entity_id(entity_id)


@pytest.mark.parametrize(
    ("entity_id", "entity_type"),
    [
        ("method.inference.anova.one_way", "method"),
        ("model.regression.linear.multiple", "model"),
        ("design.experiment.randomized_complete_block", "design"),
        ("diagnostic.normality.shapiro_wilk", "diagnostic"),
        ("algorithm.resampling.bootstrap.nonparametric", "algorithm"),
        ("measure.effect.cohens_d", "measure"),
        ("visualization.distribution.histogram", "visualization"),
        ("theory.probability.central_limit_theorem", "theory"),
        ("distribution.probability.normal", "distribution"),
    ],
)
def test_identifier_prefix_matches_entity_type(entity_id, entity_type):
    """The identifier prefix must match the entity's primary type."""
    assert validate_entity_id(
        entity_id,
        expected_entity_type=entity_type,
    ) == entity_id


def test_rejects_mismatched_entity_type():
    """A valid identifier cannot be used with the wrong entity type."""
    with pytest.raises(IdentifierValidationError):
        validate_entity_id(
            "method.inference.anova.one_way",
            expected_entity_type="model",
        )


@pytest.mark.parametrize(
    "legacy_id",
    [
        "desc.mean.arithmetic",
        "infer.t_test.independent.welch",
        "infer.anova.one_way",
        "viz.distribution.histogram",
    ],
)
def test_legacy_identifiers_are_not_canonical_ids(legacy_id):
    """Legacy identifiers require alias resolution, not canonical validation."""
    with pytest.raises(IdentifierValidationError):
        validate_entity_id(legacy_id)
