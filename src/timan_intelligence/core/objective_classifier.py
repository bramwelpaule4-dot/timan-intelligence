```python
"""Transparent classification of research objectives."""

from dataclasses import dataclass


@dataclass
class ObjectiveClassification:
    """A tentative classification of a research objective."""

    objective_type: str
    confidence: str
    matched_terms: list[str]
    explanation: str


def classify_objective(question: str) -> ObjectiveClassification:
    """Classify a research question using transparent keyword rules.

    This is an initial heuristic, not a substitute for understanding
    the research design or confirming the user's intended meaning.
    """
    if not isinstance(question, str) or not question.strip():
        return ObjectiveClassification(
            objective_type="unknown",
            confidence="low",
            matched_terms=[],
            explanation="Provide a research question or analytical objective.",
        )

    text = question.lower()

    rules = {
        "comparison": [
            "differ between",
            "difference between",
            "compare",
            "comparison",
            "higher than",
            "lower than",
            "more than",
            "less than",
            "versus",
            " vs ",
        ],
        "association": [
            "relationship between",
            "associated with",
            "association between",
            "correlation",
            "related to",
            "linked to",
        ],
        "prediction": [
            "predict",
            "prediction",
            "forecast",
            "forecasting",
            "estimate the likelihood",
        ],
        "description": [
            "describe",
            "distribution",
            "how many",
            "how much",
            "what proportion",
            "what percentage",
            "prevalence",
            "summarise",
            "summarize",
        ],
    }

    matches = {
        objective: [
            term for term in terms if term in text
        ]
        for objective, terms in rules.items()
    }

    matched_objectives = [
        objective for objective, terms in matches.items() if terms
    ]

    if len(matched_objectives) == 1:
        objective = matched_objectives[0]
        return ObjectiveClassification(
            objective_type=objective,
            confidence="moderate",
            matched_terms=matches[objective],
            explanation=(
                f"The question contains wording commonly associated with "
                f"{objective}. Confirm that this reflects the intended objective."
            ),
        )

    if len(matched_objectives) > 1:
        return ObjectiveClassification(
            objective_type="ambiguous",
            confidence="low",
            matched_terms=[
                term
                for objective in matched_objectives
                for term in matches[objective]
            ],
            explanation=(
                "The question contains wording associated with multiple "
                "objective types. Clarify the primary analytical objective."
            ),
        )

    return ObjectiveClassification(
        objective_type="unknown",
        confidence="low",
        matched_terms=[],
        explanation=(
            "The objective could not be classified using the current rules. "
            "Ask the user to clarify what they want to learn from the data."
        ),
    )
```
