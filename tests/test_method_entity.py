
def test_method_entity_initialises_method_fields_with_defaults():
    method = MethodEntity(
        entity_id="method.inference.anova.one_way",
        name="One-way ANOVA",
        description="A method for comparing group means.",
        knowledge_areas=["frequentist_inference"],
        statistical_purposes=["inferential"],
    )

    assert method.entity_type == "method"
    assert method.use_cases == []
    assert method.data_requirements == []
    assert method.statistical_specification == {}
    assert method.assumptions == []
    assert method.estimands == []
    assert method.hypotheses == []
    assert method.outputs == []
    assert method.computational_requirements == []
    assert method.validation_requirements == []
    assert method.limitations == []
