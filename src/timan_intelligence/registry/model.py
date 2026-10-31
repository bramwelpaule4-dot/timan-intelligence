
"""Tests for the TimanStat statistical model entity schema."""

from timan_intelligence.registry.contracts import RegistryEntity
from timan_intelligence.registry.model import StatisticalModelEntity


def create_model(**overrides):
    """Create a valid statistical model entity for testing."""
    values = {
        "entity_id": "model.regression.linear.multiple",
        "name": "Multiple Linear Regression Model",
        "description": (
            "A statistical model describing the relationship between "
            "a continuous outcome and multiple explanatory variables."
        ),
        "knowledge_areas": ["regression"],
        "statistical_purposes": ["inferential", "predictive"],
        "model_family": "linear_regression",
        "model_class": "linear_model",
        "response_variable": {
            "name": "income",
            "data_type": "continuous",
        },
        "predictor_variables": [
            {
                "name": "education_years",
                "role": "explanatory",
                "data_type": "continuous",
            },
            {
                "name": "experience_years",
                "role": "explanatory",
                "data_type": "continuous",
            },
        ],
        "mathematical_formulation": {
            "equation": "Y = beta_0 + beta_1*X_1 + beta_2*X_2 + epsilon",
            "response": "Y",
            "parameters": ["beta_0", "beta_1", "beta_2"],
            "error_term": "epsilon",
        },
        "parameter_definitions": {
            "beta_0": "Intercept",
            "beta_1": "Coefficient for education years",
            "beta_2": "Coefficient for experience years",
        },
        "estimation_methods": [
            "Ordinary least squares",
            "Maximum likelihood",
        ],
        "inference_methods": [
            "Wald inference",
            "Likelihood-based inference",
        ],
        "assumptions": [
            "Linearity in parameters.",
            "Independent observations.",
            "Zero conditional mean of errors.",
            "Homoscedasticity for conventional standard errors.",
        ],
        "diagnostics": [
            "Residual analysis",
            "Multicollinearity assessment",
            "Influence diagnostics",
        ],
        "outputs": [
            "Estimated coefficients",
            "Standard errors",
            "Confidence intervals",
            "Model fit statistics",
        ],
        "limitations": [
            "Sensitive to influential observations.",
            "Does not establish causality by itself.",
        ],
    }

    values.update(overrides)
    return StatisticalModelEntity(**values)


def test_model_entity_inherits_shared_registry_contract():
    model = create_model()
    assert isinstance(model, RegistryEntity)


def test_model_entity_has_model_entity_type():
    model = create_model()
    assert model.entity_type == "model"


def test_model_entity_preserves_canonical_identifier():
    model = create_model()
    assert model.entity_id == "model.regression.linear.multiple"


def test_model_entity_stores_model_classification():
    model = create_model()
    assert model.model_family == "linear_regression"
    assert model.model_class == "linear_model"


def test_model_entity_stores_response_variable():
    model = create_model()
    assert model.response_variable["name"] == "income"
    assert model.response_variable["data_type"] == "continuous"


def test_model_entity_stores_predictor_variables():
    model = create_model()
    assert len(model.predictor_variables) == 2
    assert model.predictor_variables[0]["name"] == "education_years"


def test_model_entity_stores_mathematical_formulation():
    model = create_model()
    assert "equation" in model.mathematical_formulation
    assert "parameters" in model.mathematical_formulation


def test_model_entity_stores_parameter_definitions():
    model = create_model()
    assert model.parameter_definitions["beta_0"] == "Intercept"


def test_model_entity_separates_estimation_methods():
    model = create_model()
    assert "Ordinary least squares" in model.estimation_methods
    assert "Maximum likelihood" in model.estimation_methods


def test_model_entity_separates_inference_methods():
    model = create_model()
    assert "Wald inference" in model.inference_methods
    assert "Likelihood-based inference" in model.inference_methods


def test_model_entity_stores_assumptions():
    model = create_model()
    assert len(model.assumptions) == 4
    assert "Independent observations." in model.assumptions


def test_model_entity_stores_diagnostics():
    model = create_model()
    assert "Residual analysis" in model.diagnostics
    assert "Multicollinearity assessment" in model.diagnostics


def test_model_entity_stores_outputs():
    model = create_model()
    assert "Estimated coefficients" in model.outputs
    assert "Confidence intervals" in model.outputs


def test_model_entity_stores_limitations():
    model = create_model()
    assert len(model.limitations) == 2
    assert "causality" in model.limitations[1].lower()


def test_model_entity_has_independent_mutable_collections():
    first = create_model()
    second = create_model()

    first.assumptions.append("Additional assumption.")
    first.estimation_methods.append("Additional estimator")
    first.predictor_variables.append({"name": "age"})

    assert "Additional assumption." not in second.assumptions
    assert "Additional estimator" not in second.estimation_methods
    assert len(second.predictor_variables) == 2


def test_model_entity_preserves_shared_lifecycle_fields():
    model = create_model(
        record_maturity="catalogued",
        implementation_status="planned",
        verification_status="not_tested",
    )

    assert model.record_maturity == "catalogued"
    assert model.implementation_status == "planned"
    assert model.verification_status == "not_tested"


def test_model_entity_preserves_shared_relationships():
    model = create_model()
    assert model.relationships == []
    assert model.related_entity_ids == []


def test_model_entity_initialises_model_fields_with_defaults():
    model = StatisticalModelEntity(
        entity_id="model.regression.linear.multiple",
        name="Multiple Linear Regression Model",
        description="A model describing a linear relationship.",
        knowledge_areas=["regression"],
        statistical_purposes=["inferential"],
    )

    assert model.entity_type == "model"
    assert model.model_family == ""
    assert model.model_class == ""
    assert model.response_variable == {}
    assert model.predictor_variables == []
    assert model.mathematical_formulation == {}
    assert model.parameter_definitions == {}
    assert model.estimation_methods == []
    assert model.inference_methods == []
    assert model.assumptions == []
    assert model.diagnostics == []
    assert model.outputs == []
    assert model.limitations == []
