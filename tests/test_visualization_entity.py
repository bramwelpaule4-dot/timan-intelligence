
"""Tests for the Visualisation Entity Schema."""

from dataclasses import fields

import pytest

from timan_intelligence.registry.visualization import (
    VisualizationEntity,
)


def create_visualization(**overrides):
    """Create a valid visualisation entity for testing."""
    data = {
        "entity_id": "visualization.distribution.histogram",
        "name": "Histogram",
        "description": "A graphical representation of a numerical distribution.",
        "knowledge_areas": ["descriptive_statistics"],
        "statistical_purposes": ["descriptive"],
    }
    data.update(overrides)
    return VisualizationEntity(**data)


def test_visualization_entity_can_be_created():
    entity = create_visualization()

    assert entity.name == "Histogram"
    assert entity.entity_type == "visualization"


def test_visualization_entity_inherits_shared_registry_fields():
    entity = create_visualization()

    assert entity.entity_id == "visualization.distribution.histogram"
    assert entity.description
    assert entity.knowledge_areas == ["descriptive_statistics"]
    assert entity.statistical_purposes == ["descriptive"]
    assert entity.record_maturity == "draft"


def test_entity_type_is_fixed_to_visualization():
    entity = create_visualization()

    assert entity.entity_type == "visualization"


def test_entity_type_is_not_a_constructor_argument():
    entity_fields = {
        item.name for item in fields(VisualizationEntity)
    }

    assert "entity_type" in entity_fields
    assert "entity_type" not in {
        item.name
        for item in fields(VisualizationEntity)
        if item.init
    }


def test_default_visualization_category_and_type():
    entity = create_visualization()

    assert entity.visualization_category == ""
    assert entity.visualization_type == ""


def test_visualization_definition_is_separate_from_specification():
    entity = create_visualization(
        visualization_definition={
            "purpose": "Display the distribution of a numerical variable."
        },
        visualization_specification={
            "variable": "age",
            "bins": 10,
        },
    )

    assert entity.visualization_definition["purpose"]
    assert entity.visualization_specification["variable"] == "age"
    assert entity.visualization_specification["bins"] == 10


def test_rendered_output_is_separate_from_visualization_definition():
    entity = create_visualization(
        rendered_output={
            "format": "png",
            "uri": "reports/histogram.png",
        }
    )

    assert entity.rendered_output["format"] == "png"
    assert entity.rendered_output["uri"] == "reports/histogram.png"


def test_default_visualization_structures_are_independent():
    first = create_visualization()
    second = create_visualization()

    first.visualization_specification["bins"] = 10

    assert "bins" not in second.visualization_specification


def test_variable_and_encoding_fields():
    entity = create_visualization(
        variables=["age", "income"],
        encodings={
            "x": "age",
            "y": "income",
            "color": "gender",
        },
    )

    assert entity.variables == ["age", "income"]
    assert entity.encodings["x"] == "age"
    assert entity.encodings["color"] == "gender"


def test_scales_and_facets():
    entity = create_visualization(
        scales={
            "x": "linear",
            "y": "log",
        },
        facets={
            "variable": "gender",
            "layout": "wrap",
        },
    )

    assert entity.scales["x"] == "linear"
    assert entity.scales["y"] == "log"
    assert entity.facets["variable"] == "gender"


def test_statistical_options_and_interactivity():
    entity = create_visualization(
        statistical_options={
            "confidence_interval": 0.95,
            "show_regression_line": True,
        },
        interactivity={
            "zoom": True,
            "filtering": True,
        },
    )

    assert entity.statistical_options["confidence_interval"] == 0.95
    assert entity.interactivity["zoom"] is True
    assert entity.interactivity["filtering"] is True


def test_related_statistical_entity_identifiers():
    entity = create_visualization(
        related_measure_ids=["measure.descriptive.central_tendency.mean"],
        related_model_ids=["model.regression.linear.multiple"],
        related_method_ids=["method.inference.anova.one_way"],
        related_diagnostic_ids=["diagnostic.normality.shapiro_wilk"],
    )

    assert len(entity.related_measure_ids) == 1
    assert len(entity.related_model_ids) == 1
    assert len(entity.related_method_ids) == 1
    assert len(entity.related_diagnostic_ids) == 1


def test_outputs_limitations_and_references():
    entity = create_visualization(
        outputs=["chart", "legend", "axis_labels"],
        limitations=["May be misleading with very small samples."],
        visualization_references=["Example statistical graphics reference"],
    )

    assert "chart" in entity.outputs
    assert entity.limitations
    assert entity.visualization_references


def test_visualization_defaults_are_empty_collections():
    entity = create_visualization()

    assert entity.variables == []
    assert entity.encodings == {}
    assert entity.scales == {}
    assert entity.facets == {}
    assert entity.statistical_options == {}
    assert entity.interactivity == {}
    assert entity.outputs == []
    assert entity.limitations == []


def test_visualization_entities_do_not_share_mutable_defaults():
    first = create_visualization()
    second = create_visualization()

    first.variables.append("age")
    first.outputs.append("chart")

    assert second.variables == []
    assert second.outputs == []


def test_visualization_specification_supports_different_chart_types():
    histogram = create_visualization(
        visualization_type="histogram",
        visualization_category="distribution",
    )

    scatterplot = create_visualization(
        entity_id="visualization.relationship.scatterplot",
        name="Scatterplot",
        visualization_type="scatterplot",
        visualization_category="relationship",
    )

    assert histogram.visualization_type == "histogram"
    assert scatterplot.visualization_type == "scatterplot"
    assert histogram.visualization_category == "distribution"
    assert scatterplot.visualization_category == "relationship"


def test_visualization_definition_does_not_require_rendered_output():
    entity = create_visualization(
        visualization_definition={
            "purpose": "Show the distribution of a variable."
        }
    )

    assert entity.visualization_definition
    assert entity.rendered_output == {}
