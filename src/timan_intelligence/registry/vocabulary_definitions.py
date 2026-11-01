
"""Initial controlled vocabulary definitions for TimanStat.

The initial vocabulary entries are based on the TimanStat Statistical
Methods Catalogue, Version 2.1, Section 37.

Exhaustive and illustrative classifications are preserved as specified
by the catalogue. Entity types are derived from the shared EntityType
contract to avoid maintaining duplicate authoritative lists.
"""

from __future__ import annotations

from typing import get_args

from timan_intelligence.registry.contracts import EntityType
from timan_intelligence.registry.vocabulary import (
    VocabularyDefinition,
    VocabularyMember,
)


CATALOGUE_SOURCE = (
    "TimanStat Statistical Methods Catalogue, Version 2.1, Section 37"
)

VOCABULARY_VERSION = "0.1.0"


def _make_definition(
    key: str,
    name: str,
    description: str,
    completeness: str,
) -> VocabularyDefinition:
    """Create an active, controlled vocabulary definition."""
    return VocabularyDefinition(
        vocabulary_id=f"vocab.definition.{key}",
        name=name,
        description=description,
        extensibility="controlled",
        completeness=completeness,
        status="active",
        version=VOCABULARY_VERSION,
        source=CATALOGUE_SOURCE,
    )


def _make_members(
    vocabulary_key: str,
    vocabulary_id: str,
    values: tuple[str, ...],
    descriptions: dict[str, str] | None = None,
) -> tuple[VocabularyMember, ...]:
    """Create canonical members for one vocabulary."""
    member_descriptions = descriptions or {}

    return tuple(
        VocabularyMember(
            member_id=f"vocab.{vocabulary_key}.{value}",
            vocabulary_id=vocabulary_id,
            value=value,
            label=value.replace("_", " ").title(),
            description=member_descriptions.get(value, ""),
            status="active",
            version=VOCABULARY_VERSION,
        )
        for value in values
    )


# ---------------------------------------------------------------------
# 1. Statistical purposes — exhaustive permitted values
# Catalogue: Section 37.1
# ---------------------------------------------------------------------

STATISTICAL_PURPOSES = (
    "descriptive",
    "inferential",
    "predictive",
    "causal",
    "exploratory",
    "decision_support",
    "foundational",
    "multiple",
)

STATISTICAL_PURPOSE_VOCABULARY = _make_definition(
    key="statistical_purpose",
    name="Statistical purposes",
    description=(
        "Describes the principal objective of an analysis. "
        "A method may serve more than one purpose depending "
        "on how it is used."
    ),
    completeness="exhaustive",
)

STATISTICAL_PURPOSE_MEMBERS = _make_members(
    vocabulary_key="statistical_purpose",
    vocabulary_id=STATISTICAL_PURPOSE_VOCABULARY.vocabulary_id,
    values=STATISTICAL_PURPOSES,
)


# ---------------------------------------------------------------------
# 2. Knowledge areas — illustrative examples
# Catalogue: Section 37.2
# ---------------------------------------------------------------------

KNOWLEDGE_AREAS = (
    "descriptive_statistics",
    "probability_theory",
    "frequentist_inference",
    "bayesian_statistics",
    "regression",
    "experimental_design",
    "survey_statistics",
    "multivariate_statistics",
    "nonparametric_statistics",
    "time_series",
    "survival_analysis",
    "spatial_statistics",
    "causal_inference",
    "stochastic_processes",
    "reliability_statistics",
    "epidemiology",
    "psychometrics",
    "statistical_learning",
    "mathematical_statistics",
    "longitudinal_analysis",
    "extreme_value_statistics",
    "compositional_data_analysis",
    "functional_data_analysis",
    "directional_statistics",
    "network_statistics",
    "econometrics",
)

KNOWLEDGE_AREA_VOCABULARY = _make_definition(
    key="knowledge_area",
    name="Knowledge areas",
    description=(
        "Represents broad disciplines and bodies of statistical "
        "theory. The catalogue entries are illustrative examples."
    ),
    completeness="illustrative",
)

KNOWLEDGE_AREA_MEMBERS = _make_members(
    vocabulary_key="knowledge_area",
    vocabulary_id=KNOWLEDGE_AREA_VOCABULARY.vocabulary_id,
    values=KNOWLEDGE_AREAS,
)


# ---------------------------------------------------------------------
# 3. Entity types — exhaustive primary entity types
# Catalogue: Section 37.3
# Source of values: shared EntityType contract
# ---------------------------------------------------------------------

ENTITY_TYPE_DESCRIPTIONS = {
    "method": (
        "A statistical procedure used to answer an analytical question."
    ),
    "model": (
        "A mathematical or probabilistic representation of a "
        "data-generating process or relationship."
    ),
    "design": (
        "A structure governing how observations, treatments "
        "or samples are generated."
    ),
    "diagnostic": (
        "A procedure used to assess data, assumptions or model adequacy."
    ),
    "algorithm": (
        "A computational procedure used to estimate, optimise or simulate."
    ),
    "measure": (
        "A statistic, parameter, effect size or summary quantity."
    ),
    "visualization": (
        "A graphical representation of data, estimates or model behaviour."
    ),
    "theory": (
        "A foundational statistical principle or mathematical result."
    ),
    "distribution": (
        "A probability distribution used in statistical modelling."
    ),
}

ENTITY_TYPES = get_args(EntityType)

ENTITY_TYPE_VOCABULARY = _make_definition(
    key="entity_type",
    name="Entity types",
    description=(
        "Defines the primary statistical entity classification. "
        "Each catalogue record must have one primary entity type."
    ),
    completeness="exhaustive",
)

ENTITY_TYPE_MEMBERS = _make_members(
    vocabulary_key="entity_type",
    vocabulary_id=ENTITY_TYPE_VOCABULARY.vocabulary_id,
    values=ENTITY_TYPES,
    descriptions=ENTITY_TYPE_DESCRIPTIONS,
)


# ---------------------------------------------------------------------
# 4. Method families — illustrative examples
# Catalogue: Section 37.4
# ---------------------------------------------------------------------

METHOD_FAMILIES = (
    "central_tendency",
    "dispersion",
    "distribution_shape",
    "association",
    "mean_comparison",
    "categorical_testing",
    "goodness_of_fit",
    "regression",
    "classification",
    "clustering",
    "dimension_reduction",
    "survival",
    "forecasting",
    "causal_estimation",
    "sampling_estimation",
    "variance_estimation",
    "resampling",
    "measurement",
    "reliability",
)

METHOD_FAMILY_VOCABULARY = _make_definition(
    key="method_family",
    name="Method families",
    description=(
        "Groups related statistical methods and analytical procedures. "
        "The catalogue entries are illustrative examples."
    ),
    completeness="illustrative",
)

METHOD_FAMILY_MEMBERS = _make_members(
    vocabulary_key="method_family",
    vocabulary_id=METHOD_FAMILY_VOCABULARY.vocabulary_id,
    values=METHOD_FAMILIES,
)


# ---------------------------------------------------------------------
# 5. Inference paradigms — exhaustive applicable values
# Catalogue: Section 37.5
# ---------------------------------------------------------------------

INFERENCE_PARADIGMS = (
    "frequentist",
    "bayesian",
    "randomization_based",
    "likelihood_based",
    "design_based",
    "model_based",
    "distribution_free",
    "not_applicable",
    "multiple",
)

INFERENCE_PARADIGM_VOCABULARY = _make_definition(
    key="inference_paradigm",
    name="Inference paradigms",
    description=(
        "Represents the inferential approach associated with a "
        "statistical analysis. An inference paradigm must not be "
        "confused with a knowledge area."
    ),
    completeness="exhaustive",
)

INFERENCE_PARADIGM_MEMBERS = _make_members(
    vocabulary_key="inference_paradigm",
    vocabulary_id=INFERENCE_PARADIGM_VOCABULARY.vocabulary_id,
    values=INFERENCE_PARADIGMS,
)


# ---------------------------------------------------------------------
# 6. Application domains — illustrative examples
# Catalogue: Section 37.6
# ---------------------------------------------------------------------

APPLICATION_DOMAINS = (
    "general_research",
    "biostatistics",
    "epidemiology",
    "public_health",
    "agriculture",
    "economics",
    "education",
    "business",
    "psychology",
    "engineering",
    "environmental_science",
    "social_science",
)

APPLICATION_DOMAIN_VOCABULARY = _make_definition(
    key="application_domain",
    name="Application domains",
    description=(
        "Represents fields in which statistical methods are applied. "
        "Application domains are cross-cutting tags and do not "
        "determine the mathematical identity of a method."
    ),
    completeness="illustrative",
)

APPLICATION_DOMAIN_MEMBERS = _make_members(
    vocabulary_key="application_domain",
    vocabulary_id=APPLICATION_DOMAIN_VOCABULARY.vocabulary_id,
    values=APPLICATION_DOMAINS,
)


# ---------------------------------------------------------------------
# Initial catalogue collections
# ---------------------------------------------------------------------

INITIAL_VOCABULARIES = (
    STATISTICAL_PURPOSE_VOCABULARY,
    KNOWLEDGE_AREA_VOCABULARY,
    ENTITY_TYPE_VOCABULARY,
    METHOD_FAMILY_VOCABULARY,
    INFERENCE_PARADIGM_VOCABULARY,
    APPLICATION_DOMAIN_VOCABULARY,
)

INITIAL_VOCABULARY_MEMBERS = (
    *STATISTICAL_PURPOSE_MEMBERS,
    *KNOWLEDGE_AREA_MEMBERS,
    *ENTITY_TYPE_MEMBERS,
    *METHOD_FAMILY_MEMBERS,
    *INFERENCE_PARADIGM_MEMBERS,
    *APPLICATION_DOMAIN_MEMBERS,
)
