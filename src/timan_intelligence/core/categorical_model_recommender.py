"""Transparent recommendations for categorical-outcome regression models."""

from __future__ import annotations

import pandas as pd


def recommend_categorical_outcome_model(
    df: pd.DataFrame,
    outcome_variable: str,
    category_structure: str | None = None,
) -> dict:
    """Recommend a model from category count and analyst-confirmed structure.

    Category ordering is a substantive property and is never inferred from
    alphabetical, numeric, or observed row order. For outcomes with 3+ levels,
    callers must identify whether the categories are ordered or nominal.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input data must be a pandas DataFrame.")
    if df.empty:
        raise ValueError("The dataset contains no records.")
    if outcome_variable not in df.columns:
        raise ValueError(f"Outcome variable '{outcome_variable}' was not found.")

    observed = df[outcome_variable].dropna()
    categories = list(pd.unique(observed))
    category_count = len(categories)
    counts = observed.value_counts(dropna=False)
    distribution = {str(category): int(counts.loc[category]) for category in categories}
    missing_n = int(df[outcome_variable].isna().sum())

    base = {
        "outcome_variable": outcome_variable,
        "category_count": category_count,
        "category_counts": distribution,
        "valid_n": int(len(observed)),
        "missing_n": missing_n,
        "category_structure": category_structure,
        "recommended_model": None,
        "status": "ready",
        "rationale": [],
        "warnings": [],
    }

    if category_count < 2:
        base["status"] = "not_suitable"
        base["rationale"].append(
            "The selected outcome has fewer than two observed categories; categorical regression cannot be fitted."
        )
        return base

    if category_count == 2:
        if category_structure not in (None, "binary"):
            raise ValueError("A two-category outcome must use the binary structure.")
        base["category_structure"] = "binary"
        base["recommended_model"] = "binary_logistic"
        base["rationale"].append(
            "The outcome has exactly two observed categories. Binary logistic regression models the probability of a clearly defined event category."
        )
        base["rationale"].append(
            "The analyst must explicitly identify which category represents the event of interest before fitting the model."
        )
    else:
        if category_structure not in ("ordered", "nominal"):
            base["status"] = "needs_classification"
            base["rationale"].append(
                "Three or more categories are present. Confirm whether they have a meaningful substantive order; the software will not infer this from their labels or stored order."
            )
            base["rationale"].append(
                "Choose ordinal logistic regression for genuinely ordered levels, or multinomial logistic regression for unordered categories."
            )
        elif category_structure == "ordered":
            base["recommended_model"] = "ordinal_logistic"
            base["rationale"].append(
                "The analyst has confirmed that the outcome categories have a meaningful order. Ordinal logistic regression is the initial candidate."
            )
            base["warnings"].append(
                "The proportional-odds assumption must be assessed; the current guided model does not yet provide a formal test of this assumption."
            )
        else:
            base["recommended_model"] = "multinomial_logistic"
            base["rationale"].append(
                "The analyst has confirmed that the outcome categories are nominal and have no meaningful order. Multinomial logistic regression is the initial candidate."
            )
            base["warnings"].append(
                "Consider whether the independence-of-irrelevant-alternatives assumption is reasonable for the outcome categories."
            )

    if len(observed) and int(counts.min()) < 20:
        base["warnings"].append(
            "At least one outcome category has fewer than 20 observations. Estimates may be unstable; check category frequencies and model complexity."
        )
    if missing_n:
        base["warnings"].append(
            f"{missing_n:,} record(s) have a missing outcome and will not contribute to a model fitted to this outcome."
        )
    return base
