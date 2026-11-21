
"""Rule-based statistical method selection and eligibility assessment.

This module recommends candidate methods and assesses a user's preferred
method using the information supplied. It does not execute statistical tests
or claim that unverified assumptions have been satisfied.
"""

from dataclasses import dataclass, field

from timan_intelligence.registry.method_catalogue import get_statistical_methods


ELIGIBLE = "eligible"
CONDITIONALLY_ELIGIBLE = "conditionally_eligible"
INSUFFICIENT_INFORMATION = "insufficient_information"
INELIGIBLE = "ineligible"


@dataclass
class MethodCandidate:
    """A candidate statistical method and its review requirements."""

    method: str
    rationale: str
    checks: list[str] = field(default_factory=list)
    status: str = "review_required"
    catalogue: dict[str, object] = field(default_factory=dict)


@dataclass
class MethodAssessment:
    """Assessment of a user's preferred statistical method."""

    preferred_method: str
    eligibility: str
    rationale: str
    clarification_questions: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    alternatives: list[MethodCandidate] = field(default_factory=list)
    status: str = "review_required"
    catalogue: dict[str, object] = field(default_factory=dict)


def _normalise_method_label(value: str) -> str:
    """Normalise method labels for matching registry names and aliases."""
    return " ".join(value.casefold().split())


def _find_catalogue_method(label: str):
    """Resolve a display label or alias against the authoritative catalogue."""
    normalised = _normalise_method_label(label)
    for record in get_statistical_methods():
        labels = [record.name, *record.aliases]
        if any(_normalise_method_label(item) == normalised for item in labels):
            return record
    return None


def _catalogue_metadata(label: str) -> dict[str, object]:
    """Expose lifecycle and design metadata without implying executability."""
    record = _find_catalogue_method(label)
    if record is None:
        return {}
    specification = record.statistical_specification or {}
    return {
        "method_id": record.entity_id,
        "implementation_status": record.implementation_status,
        "verification_status": record.verification_status,
        "execution_eligibility": record.execution_eligibility,
        "sampling_design_aware": bool(
            specification.get("sampling_design_aware", False)
        ),
        "catalogue_version": record.metadata.get("catalogue_version"),
        "release_priority": record.metadata.get("release_priority"),
        "outcome_types": list(specification.get("outcome_types", [])),
        "predictor_types": list(specification.get("predictor_types", [])),
        "required_variable_roles": list(
            specification.get("required_variable_roles", [])
        ),
        "compatible_study_designs": list(
            specification.get("compatible_study_designs", [])
        ),
    }


def catalogue_metadata_for_method(label: str) -> dict[str, object]:
    """Public planner helper for attaching authoritative catalogue metadata."""
    return _catalogue_metadata(label)


def _missing_required_roles(
    metadata: dict[str, object],
    available_variable_roles: set[str] | None,
) -> list[str]:
    """Return catalogue-required roles that have not been explicitly supplied."""
    if available_variable_roles is None:
        return []
    required = metadata.get("required_variable_roles", [])
    return [role for role in required if role not in available_variable_roles]


def _attach_catalogue_metadata(
    candidates: list[MethodCandidate],
    outcome_type: str | None = None,
    predictor_type: str | None = None,
    study_design: str | None = None,
    available_variable_roles: set[str] | None = None,
) -> list[MethodCandidate]:
    """Apply catalogue type/design constraints and attach authoritative metadata.

    Empty catalogue constraints mean that the catalogue has not specified a
    restriction; they are not interpreted as proof of universal compatibility.
    """
    registered = []
    for candidate in candidates:
        metadata = _catalogue_metadata(candidate.method)
        if not metadata:
            continue

        allowed_outcomes = metadata["outcome_types"]
        if outcome_type is not None and allowed_outcomes and outcome_type not in allowed_outcomes:
            continue

        allowed_predictors = metadata["predictor_types"]
        if predictor_type is not None and allowed_predictors and predictor_type not in allowed_predictors:
            continue

        allowed_designs = metadata["compatible_study_designs"]
        if study_design is not None and allowed_designs and study_design not in allowed_designs:
            continue

        if _missing_required_roles(metadata, available_variable_roles):
            continue

        candidate.catalogue = metadata
        registered.append(candidate)
    return registered


def select_methods(
    objective_type: str,
    outcome_type: str | None = None,
    predictor_type: str | None = None,
    group_count: int | None = None,
    independent_groups: bool | None = None,
    study_design: str | None = None,
    available_variable_roles: set[str] | None = None,
) -> list[MethodCandidate]:
    """Return candidate methods from the supplied objective and data types.

    Recommendations are preliminary. Study design, data quality, assumptions,
    sample size and method-specific requirements must still be reviewed.
    """
    candidates = []

    if objective_type == "description":
        if outcome_type in {"categorical", "binary", "ordinal"}:
            candidates.append(
                MethodCandidate(
                    method="Frequencies and proportions",
                    rationale=(
                        "Describe the distribution of a categorical outcome."
                    ),
                    checks=[
                        "Review missing and invalid category values.",
                        "Confirm whether survey weights are required.",
                    ],
                )
            )

        elif outcome_type == "numeric":
            candidates.append(
                MethodCandidate(
                    method="Descriptive statistics",
                    rationale=(
                        "Summarise the centre, spread and distribution "
                        "of a numeric variable."
                    ),
                    checks=[
                        "Review missing values and implausible observations.",
                        "Inspect the distribution and potential outliers.",
                    ],
                )
            )

    elif objective_type == "comparison":
        if (
            outcome_type == "numeric"
            and group_count == 2
            and independent_groups is True
        ):
            candidates.extend(
                [
                    MethodCandidate(
                        method="Independent-samples t-test",
                        rationale=(
                            "Compare mean values between two independent groups."
                        ),
                        checks=[
                            "Check independence of observations.",
                            "Assess distributional assumptions and outliers.",
                            "Assess variance assumptions or consider Welch's t-test.",
                        ],
                    ),
                    MethodCandidate(
                        method="Mann–Whitney U test",
                        rationale=(
                            "Compare two independent groups using a rank-based "
                            "approach when appropriate."
                        ),
                        checks=[
                            "Check independence of observations.",
                            "Interpret the result according to the outcome "
                            "distributions; it is not automatically a test "
                            "of medians.",
                        ],
                    ),
                ]
            )

        elif (
            outcome_type == "numeric"
            and group_count is not None
            and group_count >= 3
            and independent_groups is True
        ):
            candidates.extend(
                [
                    MethodCandidate(
                        method="One-way ANOVA",
                        rationale=(
                            "Compare mean values across three or more "
                            "independent groups when the method's assumptions "
                            "are reasonably satisfied."
                        ),
                        checks=[
                            "Check independence of observations.",
                            "Assess residual distribution and variance assumptions.",
                            "Review outliers and consider appropriate post-hoc comparisons.",
                        ],
                    ),
                    MethodCandidate(
                        method="Kruskal–Wallis test",
                        rationale=(
                            "Compare three or more independent groups using "
                            "a rank-based approach when appropriate."
                        ),
                        checks=[
                            "Check independence of observations.",
                            "Review group distributions and sample sizes.",
                            "If results are significant, consider appropriate "
                            "post-hoc comparisons with multiplicity control.",
                        ],
                    ),
                ]
            )

        elif (
            outcome_type in {"categorical", "binary"}
            and group_count == 2
            and independent_groups is True
        ):
            candidates.extend(
                [
                    MethodCandidate(
                        method="Chi-square test of independence",
                        rationale=(
                            "Assess whether two categorical variables are associated."
                        ),
                        checks=[
                            "Inspect expected cell counts.",
                            "Check independence of observations.",
                        ],
                    ),
                    MethodCandidate(
                        method="Fisher's exact test",
                        rationale=(
                            "Consider for a 2 × 2 table when expected counts "
                            "are too small for a reliable chi-square approximation."
                        ),
                        checks=[
                            "Confirm that the table is 2 × 2.",
                            "Check independence of observations.",
                        ],
                    ),
                ]
            )

    elif objective_type == "association":
        if outcome_type == "numeric" and predictor_type == "numeric":
            candidates.extend(
                [
                    MethodCandidate(
                        method="Pearson correlation",
                        rationale=(
                            "Assess the strength and direction of a linear "
                            "relationship between two numeric variables."
                        ),
                        checks=[
                            "Inspect a scatterplot for linearity and outliers.",
                            "Review assumptions relevant to inference.",
                            "Correlation does not establish causation.",
                        ],
                    ),
                    MethodCandidate(
                        method="Spearman rank correlation",
                        rationale=(
                            "Assess a monotonic relationship using ranked values."
                        ),
                        checks=[
                            "Inspect the relationship and potential outliers.",
                            "Correlation does not establish causation.",
                        ],
                    ),
                ]
            )

        elif (
            outcome_type in {"categorical", "binary"}
            and predictor_type in {"categorical", "binary"}
        ):
            candidates.extend(
                [
                    MethodCandidate(
                        method="Chi-square test of independence",
                        rationale=(
                            "Assess association between two categorical variables."
                        ),
                        checks=[
                            "Inspect expected cell counts.",
                            "Check independence of observations.",
                        ],
                    ),
                    MethodCandidate(
                        method="Fisher's exact test",
                        rationale=(
                            "Consider for a 2 × 2 table with small expected counts."
                        ),
                        checks=[
                            "Confirm that the table is 2 × 2.",
                            "Check independence of observations.",
                        ],
                    ),
                ]
            )

    elif objective_type == "prediction":
        if outcome_type == "binary":
            candidates.append(
                MethodCandidate(
                    method="Logistic regression",
                    rationale=(
                        "Model the probability of a binary outcome using "
                        "one or more predictors."
                    ),
                    checks=[
                        "Check sample size and outcome-class counts.",
                        "Review missingness, separation and model specification.",
                        "Evaluate model performance using an appropriate validation plan.",
                    ],
                )
            )

        elif outcome_type == "numeric":
            candidates.append(
                MethodCandidate(
                    method="Linear regression",
                    rationale=(
                        "Model a numeric outcome using one or more predictors."
                    ),
                    checks=[
                        "Review linearity and residual behaviour.",
                        "Check influential observations and multicollinearity.",
                        "Evaluate predictive performance using appropriate validation.",
                    ],
                )
            )

    return _attach_catalogue_metadata(
        candidates,
        outcome_type=outcome_type,
        predictor_type=predictor_type,
        study_design=study_design,
        available_variable_roles=available_variable_roles,
    )


def assess_preferred_method(
    preferred_method: str,
    objective_type: str,
    outcome_type: str | None = None,
    predictor_type: str | None = None,
    group_count: int | None = None,
    independent_groups: bool | None = None,
    study_design: str | None = None,
    available_variable_roles: set[str] | None = None,
) -> MethodAssessment:
    """Assess a preferred method before suggesting alternatives.

    This rule-based assessment identifies basic incompatibilities and missing
    design information. It does not inspect a dataset or verify assumptions.
    """
    method = (
        preferred_method.strip()
        if isinstance(preferred_method, str)
        else ""
    )

    if not method:
        return MethodAssessment(
            preferred_method="",
            eligibility=INSUFFICIENT_INFORMATION,
            rationale="A preferred method was not supplied.",
            clarification_questions=[
                "Which statistical method would you like assessed, if you have one in mind?"
            ],
            alternatives=select_methods(
                objective_type,
                outcome_type,
                predictor_type,
                group_count,
                independent_groups,
                study_design,
                available_variable_roles,
            ),
        )

    registry_method = _find_catalogue_method(method)
    if registry_method is None:
        return MethodAssessment(
            preferred_method=method,
            eligibility=INSUFFICIENT_INFORMATION,
            rationale=(
                "This method is not yet recognised by the initial method "
                "assessment rules. Its suitability cannot be established."
            ),
            clarification_questions=[
                "Can you confirm the method's exact name or describe the analysis you want to perform?"
            ],
            alternatives=select_methods(
                objective_type,
                outcome_type,
                predictor_type,
                group_count,
                independent_groups,
                study_design,
                available_variable_roles,
            ),
        )

    specification = registry_method.statistical_specification or {}
    allowed_outcomes = list(specification.get("outcome_types", []))
    allowed_predictors = list(specification.get("predictor_types", []))
    allowed_designs = list(specification.get("compatible_study_designs", []))

    if outcome_type is not None and allowed_outcomes and outcome_type not in allowed_outcomes:
        return MethodAssessment(
            preferred_method=method,
            eligibility=INELIGIBLE,
            rationale=(
                f"{registry_method.name} does not support the supplied "
                f"outcome type '{outcome_type}' according to the catalogue."
            ),
            alternatives=select_methods(
                objective_type, outcome_type, predictor_type, group_count,
                independent_groups, study_design, available_variable_roles,
            ),
            catalogue=_catalogue_metadata(method),
        )

    if predictor_type is not None and allowed_predictors and predictor_type not in allowed_predictors:
        return MethodAssessment(
            preferred_method=method,
            eligibility=INELIGIBLE,
            rationale=(
                f"{registry_method.name} does not support the supplied "
                f"predictor type '{predictor_type}' according to the catalogue."
            ),
            alternatives=select_methods(
                objective_type, outcome_type, predictor_type, group_count,
                independent_groups, study_design, available_variable_roles,
            ),
            catalogue=_catalogue_metadata(method),
        )

    if study_design is not None and allowed_designs and study_design not in allowed_designs:
        return MethodAssessment(
            preferred_method=method,
            eligibility=INELIGIBLE,
            rationale=(
                f"{registry_method.name} is not catalogued for the supplied "
                f"study design '{study_design}'."
            ),
            alternatives=select_methods(
                objective_type, outcome_type, predictor_type, group_count,
                independent_groups, study_design, available_variable_roles,
            ),
            catalogue=_catalogue_metadata(method),
        )

    missing_roles = _missing_required_roles(
        _catalogue_metadata(method),
        available_variable_roles,
    )
    if missing_roles:
        return MethodAssessment(
            preferred_method=method,
            eligibility=INSUFFICIENT_INFORMATION,
            rationale=(
                "The selected method requires additional variable roles: "
                + ", ".join(missing_roles)
                + ". These roles have not been identified in the analysis request."
            ),
            clarification_questions=[
                "Identify the dataset column for each required role: "
                + ", ".join(missing_roles)
                + "."
            ],
            alternatives=select_methods(
                objective_type, outcome_type, predictor_type, group_count,
                independent_groups, study_design, available_variable_roles,
            ),
            catalogue=_catalogue_metadata(method),
        )

    assessable_methods = {
        "Descriptive statistics",
        "Frequencies and proportions",
        "Independent-samples t-test",
        "Mann–Whitney U test",
        "Paired-samples t-test",
        "One-way ANOVA",
        "Kruskal–Wallis test",
        "Chi-square test of independence",
        "Fisher's exact test",
        "Pearson correlation",
        "Spearman rank correlation",
        "Logistic regression",
        "Linear regression",
    }
    if method not in assessable_methods:
        return MethodAssessment(
            preferred_method=method,
            eligibility=INSUFFICIENT_INFORMATION,
            rationale=(
                "This method is present in the statistical catalogue, but "
                "method-specific suitability rules have not yet been added."
            ),
            clarification_questions=[
                "This method is catalogued but cannot yet be assessed automatically."
            ],
            alternatives=select_methods(
                objective_type,
                outcome_type,
                predictor_type,
                group_count,
                independent_groups,
                study_design,
                available_variable_roles,
            ),
            catalogue=_catalogue_metadata(method),
        )

    questions = []
    checks = [
        "Review the study design and variable coding.",
        "Assess relevant assumptions using the dataset and study context.",
        "Check missingness, sample size and influential observations where applicable.",
    ]
    reason = ""
    eligibility = CONDITIONALLY_ELIGIBLE

    if method == "Descriptive statistics":
        if objective_type != "description" or outcome_type != "numeric":
            eligibility = INELIGIBLE
            reason = (
                "Descriptive statistics for a numeric variable do not match "
                "the supplied objective or outcome type."
            )
        else:
            reason = (
                "The objective and numeric outcome are compatible with "
                "descriptive statistics."
            )

    elif method == "Frequencies and proportions":
        if objective_type != "description" or outcome_type not in {
            "categorical",
            "binary",
            "ordinal",
        }:
            eligibility = INELIGIBLE
            reason = (
                "Frequencies and proportions require a categorical outcome "
                "for this descriptive workflow."
            )
        else:
            reason = (
                "The objective and categorical outcome are compatible with "
                "frequencies and proportions."
            )

    elif method in {"Independent-samples t-test", "Mann–Whitney U test"}:
        if objective_type != "comparison" or outcome_type != "numeric":
            eligibility = INELIGIBLE
            reason = (
                "This method requires a comparison objective with a numeric outcome."
            )
        elif group_count is None or independent_groups is None:
            eligibility = INSUFFICIENT_INFORMATION
            reason = "The number of groups or their independence is unknown."
            questions.extend(
                [
                    "How many groups are being compared?",
                    "Are the groups independent, or are the same participants measured more than once?",
                ]
            )
        elif group_count != 2 or independent_groups is not True:
            eligibility = INELIGIBLE
            reason = (
                "This method requires two independent groups. The supplied "
                "design does not meet that requirement."
            )
        else:
            reason = (
                "The supplied objective, numeric outcome and independent "
                "two-group design are compatible; assumptions still require review."
            )

    elif method in {"Paired-samples t-test", "Wilcoxon signed-rank test"}:
        if objective_type != "comparison" or outcome_type != "numeric":
            eligibility = INELIGIBLE
            reason = (
                "This method requires a comparison objective with a numeric outcome."
            )
        elif independent_groups is True:
            eligibility = INELIGIBLE
            reason = "A paired method is not appropriate for independent groups."
        elif independent_groups is None:
            eligibility = INSUFFICIENT_INFORMATION
            reason = "It is not known whether observations are paired."
            questions.append(
                "Are these paired measurements, such as the same participants measured before and after an intervention?"
            )
        else:
            reason = (
                "The supplied design indicates paired observations; "
                "method-specific assumptions still require review."
            )

    elif method in {"One-way ANOVA", "Kruskal–Wallis test"}:
        if objective_type != "comparison" or outcome_type != "numeric":
            eligibility = INELIGIBLE
            reason = (
                "This method requires a comparison objective with a numeric outcome."
            )
        elif group_count is None or independent_groups is None:
            eligibility = INSUFFICIENT_INFORMATION
            reason = (
                "The number of groups or their independence has not been supplied."
            )
            questions.append(
                "How many groups are being compared, and are the groups independent?"
            )
        elif group_count < 3 or independent_groups is not True:
            eligibility = INELIGIBLE
            reason = (
                "This initial implementation requires at least three "
                "independent groups for these methods."
            )
        else:
            reason = (
                "The supplied design is compatible with a multi-group comparison; "
                "assumptions and follow-up comparisons require review."
            )

    elif method in {
        "Chi-square test of independence",
        "Fisher's exact test",
    }:
        if (
            objective_type not in {"comparison", "association"}
            or outcome_type not in {"categorical", "binary"}
        ):
            eligibility = INELIGIBLE
            reason = (
                "This method requires a categorical association or comparison objective."
            )
        else:
            reason = (
                "The objective and categorical outcome may be compatible. "
                "The contingency-table structure and expected counts must be assessed."
            )
            checks.extend(
                [
                    "Inspect the observed and expected contingency-table counts.",
                    "Confirm table dimensions; the standard Fisher's exact test is for a 2 × 2 table.",
                ]
            )
            questions.append(
                "What are the two categorical variables, and how many categories does each have?"
            )

    elif method in {"Pearson correlation", "Spearman rank correlation"}:
        if (
            objective_type != "association"
            or outcome_type != "numeric"
            or predictor_type != "numeric"
        ):
            eligibility = INELIGIBLE
            reason = (
                "This correlation workflow requires an association objective "
                "and two numeric variables."
            )
        else:
            reason = (
                "The two numeric variables are compatible with correlation "
                "analysis; inspect the relationship before choosing the correlation coefficient."
            )

    elif method in {"Logistic regression", "Linear regression"}:
        expected_type = "binary" if method == "Logistic regression" else "numeric"
        if objective_type != "prediction" or outcome_type != expected_type:
            eligibility = INELIGIBLE
            reason = (
                f"{method} does not match the supplied objective and outcome type."
            )
        else:
            reason = (
                "The objective and outcome type are compatible with this regression model. "
                "Predictors, sample size, model specification and validation still require assessment."
            )
            questions.append(
                "Which predictor variables will be included in the model?"
            )

    alternatives = [
        candidate
        for candidate in select_methods(
            objective_type,
            outcome_type,
            predictor_type,
            group_count,
            independent_groups,
            study_design,
            available_variable_roles,
        )
        if candidate.method != method
    ]

    if eligibility == INELIGIBLE and not alternatives:
        questions.append(
            "Would you like to provide more details about the study design so suitable alternatives can be identified?"
        )

    return MethodAssessment(
        preferred_method=method,
        eligibility=eligibility,
        rationale=reason,
        clarification_questions=questions,
        checks=checks,
        alternatives=alternatives,
        catalogue=_catalogue_metadata(method),
    )
