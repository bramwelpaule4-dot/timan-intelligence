from timan_intelligence.core.objective_classifier import classify_objective


def test_classifies_comparison_objective():
    result = classify_objective(
        "Does access to clean water differ between male-headed "
        "and female-headed households?"
    )

    assert result.objective_type == "comparison"
    assert result.confidence == "moderate"


def test_classifies_association_objective():
    result = classify_objective(
        "Is household income associated with education level?"
    )

    assert result.objective_type == "association"


def test_classifies_prediction_objective():
    result = classify_objective(
        "Can household income predict food security?"
    )

    assert result.objective_type == "prediction"


def test_classifies_description_objective():
    result = classify_objective(
        "What proportion of households have access to clean water?"
    )

    assert result.objective_type == "description"


def test_identifies_ambiguous_objective():
    result = classify_objective(
        "Compare the relationship between age and income."
    )

    assert result.objective_type == "ambiguous"
    assert result.confidence == "low"


def test_handles_empty_question():
    result = classify_objective("   ")

    assert result.objective_type == "unknown"
    assert result.confidence == "low"


def test_handles_unrecognised_question():
    result = classify_objective(
        "What factors explain household food insecurity?"
    )

    assert result.objective_type == "unknown"
    assert result.confidence == "low"


def test_returns_matched_terms():
    result = classify_objective(
        "Compare income between two groups."
    )

    assert "compare" in result.matched_terms
