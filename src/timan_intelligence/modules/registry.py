"""Central catalogue of domains and planned analytical capabilities."""

DOMAINS = {
    "ngo_meal": {
        "label": "NGO and MEAL",
        "capabilities": [
            "indicator_monitoring",
            "disaggregation",
            "household_survey_analysis",
            "data_quality_assessment",
            "feedback_analysis",
            "trend_reporting",
        ],
    },
    "research": {
        "label": "Research and academic statistics",
        "capabilities": [
            "descriptive_statistics",
            "hypothesis_testing",
            "confidence_intervals",
            "regression",
            "model_diagnostics",
            "reproducible_reporting",
        ],
    },
    "business": {
        "label": "Business analytics",
        "capabilities": [
            "sales_analysis",
            "cost_and_margin_analysis",
            "inventory_analysis",
            "customer_segmentation",
            "forecasting",
            "scenario_optimisation",
        ],
    },
}

# Status is explicit so the interface does not present planned functionality
# as if it were already implemented.
CAPABILITY_STATUS = {
    "data_import_csv_excel": "implemented",
    "data_quality_profile": "implemented",
    "descriptive_statistics": "initial",
    "indicator_monitoring": "planned",
    "household_survey_analysis": "planned",
    "hypothesis_testing": "planned",
    "confidence_intervals": "planned",
    "regression": "planned",
    "sales_analysis": "planned",
    "forecasting": "planned",
    "scenario_optimisation": "planned",
    "ai_question_interpretation": "planned",
    "report_generation": "planned",
}


def get_domain_catalogue() -> dict:
    """Return the configured domain catalogue."""
    return DOMAINS
