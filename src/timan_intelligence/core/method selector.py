
"""Rule-based selection of candidate statistical methods.

This module suggests methods but does not execute statistical tests.
Final selection requires review of the study design, variable coding,
sample size and method-specific assumptions.
"""

from dataclasses import dataclass, field


@dataclass
class MethodCandidate:
    """A candidate statistical method and its review requirements."""

    method: str
    rationale: str
    checks: list[str] = field(default_factory=list)
    status: str = "review_required"


def select_methods(
    objective_type: str,
    outcome_type: str | None = None,
    predictor_type: str | None = None,
    group_count: int | None = None,
    independent_groups: bool | None = None,
) -> list[MethodCandidate]:
    """Return candidate methods using objective and variable characteristics.

    Variable types should be supplied explicitly:
    - numeric
    - categorical
    - binary
    - ordinal

    This initial selector is deliberately conservative.
    It does not infer study design or execute tests.
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
                            "Consider for comparing two independent groups "
                            "when a rank-based approach is appropriate."
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

        elif outcome_type in {"categorical", "binary"} and predictor_type in {
            "categorical",
            "binary",
        }:
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

    return candidates
