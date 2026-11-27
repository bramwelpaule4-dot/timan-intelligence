import pandas as pd
import pytest

from timan_intelligence.core.statistical_engine import (
    run_descriptive_statistics,
)


def test_descriptive_statistics_returns_correct_results():
    df = pd.DataFrame({"income": [10, 20, 30, 40, 50]})

    result = run_descriptive_statistics(df, "income")
    summary = result.tables["summary"]

    assert result.status == "success"
    assert result.method == "Descriptive statistics"
    assert summary["observations"] == 5
    assert summary["missing_values"] == 0
    assert summary["mean"] == pytest.approx(30.0)
    assert summary["median"] == pytest.approx(30.0)
    assert summary["standard_deviation"] == pytest.approx(
        15.811388300841896
    )
    assert summary["minimum"] == pytest.approx(10.0)
    assert summary["maximum"] == pytest.approx(50.0)
    assert summary["q1"] == pytest.approx(20.0)
    assert summary["q3"] == pytest.approx(40.0)


def test_descriptive_statistics_excludes_and_reports_missing_values():
    df = pd.DataFrame({"score": [10, None, 30]})

    result = run_descriptive_statistics(df, "score")
    summary = result.tables["summary"]

    assert summary["observations"] == 2
    assert summary["missing_values"] == 1
    assert summary["mean"] == pytest.approx(20.0)


def test_descriptive_statistics_handles_one_observation():
    df = pd.DataFrame({"score": [7]})

    result = run_descriptive_statistics(df, "score")
    summary = result.tables["summary"]

    assert summary["observations"] == 1
    assert summary["mean"] == pytest.approx(7.0)
    assert summary["standard_deviation"] is None
    assert len(result.limitations) > 0


def test_descriptive_statistics_rejects_missing_variable():
    df = pd.DataFrame({"income": [10, 20, 30]})

    with pytest.raises(ValueError, match="not found"):
        run_descriptive_statistics(df, "expenditure")


def test_descriptive_statistics_rejects_non_numeric_variable():
    df = pd.DataFrame({"ward": ["A", "B", "A"]})

    with pytest.raises(TypeError, match="must be numeric"):
        run_descriptive_statistics(df, "ward")


def test_descriptive_statistics_rejects_all_missing_values():
    df = pd.DataFrame({"score": [None, None]})

    with pytest.raises(ValueError, match="no usable numeric observations"):
        run_descriptive_statistics(df, "score")


def test_descriptive_statistics_rejects_non_dataframe_input():
    with pytest.raises(TypeError, match="DataFrame"):
        run_descriptive_statistics([10, 20, 30], "income")


def test_descriptive_statistics_does_not_modify_original_data():
    df = pd.DataFrame({"income": [10, None, 30]})
    original = df.copy(deep=True)

    run_descriptive_statistics(df, "income")

    pd.testing.assert_frame_equal(df, original)


def test_descriptive_statistics_handles_empty_dataframe():
    df = pd.DataFrame({"score": pd.Series(dtype="float64")})

    with pytest.raises(ValueError, match="no usable numeric observations"):
        run_descriptive_statistics(df, "score")


def test_descriptive_statistics_handles_constant_values():
    df = pd.DataFrame({"score": [5, 5, 5, 5]})

    result = run_descriptive_statistics(df, "score")
    summary = result.tables["summary"]

    assert summary["observations"] == 4
    assert summary["mean"] == pytest.approx(5.0)
    assert summary["median"] == pytest.approx(5.0)
    assert summary["standard_deviation"] == pytest.approx(0.0)
    assert summary["minimum"] == pytest.approx(5.0)
    assert summary["maximum"] == pytest.approx(5.0)


def test_descriptive_statistics_handles_infinite_values():
    df = pd.DataFrame(
        {"score": [10.0, float("inf"), 20.0, float("-inf"), None]}
    )

    result = run_descriptive_statistics(df, "score")
    summary = result.tables["summary"]

    assert summary["observations"] == 2
    assert summary["mean"] == pytest.approx(15.0)
    assert summary["minimum"] == pytest.approx(10.0)
    assert summary["maximum"] == pytest.approx(20.0)

    # This assertion assumes the engine reports infinite values separately.
    assert summary["infinite_values"] == 2
    assert summary["missing_values"] == 1


def test_descriptive_statistics_rejects_all_non_finite_values():
    df = pd.DataFrame(
        {"score": [float("inf"), float("-inf"), None]}
    )

    with pytest.raises(ValueError, match="no usable numeric observations"):
        run_descriptive_statistics(df, "score")


def test_descriptive_statistics_handles_zero_as_valid_data():
    df = pd.DataFrame({"score": [0, 0, 10]})

    result = run_descriptive_statistics(df, "score")
    summary = result.tables["summary"]

    assert summary["observations"] == 3
    assert summary["mean"] == pytest.approx(10 / 3)
    assert summary["minimum"] == pytest.approx(0.0)


def test_descriptive_statistics_does_not_modify_data_with_infinities():
    df = pd.DataFrame({"score": [10.0, float("inf"), 20.0]})
    original = df.copy(deep=True)

    run_descriptive_statistics(df, "score")

    pd.testing.assert_frame_equal(df, original)


def test_linear_mixed_effects_model_fits_random_intercept_and_fixed_time_effect():
    from timan_intelligence.core.statistical_engine import run_linear_mixed_effects_model
    rows = []
    for subject in range(1, 13):
        for time in range(4):
            rows.append({"subject": f"S{subject}", "time": float(time),
                         "score": subject * 0.35 + 1.8 * time + ((subject + time) % 3) * 0.08})
    result = run_linear_mixed_effects_model(pd.DataFrame(rows), "score", "subject", ["time"])
    assert result.status == "success"
    assert result.metadata["converged"] is True
    assert result.metadata["n_groups"] == 12
    assert result.tables["fixed_effects"].loc[1, "Coefficient"] == pytest.approx(1.8, abs=0.15)
    assert result.metadata["random_intercept_variance"] >= 0
    assert "model_summary" in result.tables


def test_linear_mixed_effects_model_handles_categorical_predictor_and_missing_rows():
    from timan_intelligence.core.statistical_engine import run_linear_mixed_effects_model
    rows = []
    for subject in range(1, 9):
        for visit, arm in enumerate(["control", "treatment", "treatment"]):
            rows.append({"subject": subject, "visit": float(visit), "arm": arm,
                         "score": subject * 0.2 + visit + (arm == "treatment") * 2.0})
    frame = pd.DataFrame(rows)
    frame.loc[0, "score"] = None
    result = run_linear_mixed_effects_model(frame, "score", "subject", ["visit", "arm"])
    assert result.metadata["missing_rows_excluded"] == 1
    assert result.metadata["n_observations"] == len(frame) - 1
    assert len(result.tables["fixed_effects"]) == 3


def test_linear_mixed_effects_model_rejects_constant_predictor():
    from timan_intelligence.core.statistical_engine import run_linear_mixed_effects_model
    frame = pd.DataFrame({"subject": [1,1,2,2,3,3], "score": [1,2,2,3,3,4], "constant": [1]*6})
    with pytest.raises(ValueError, match="two observed values"):
        run_linear_mixed_effects_model(frame, "score", "subject", ["constant"])


def test_linear_mixed_effects_model_uses_requested_confidence_level():
    from timan_intelligence.core.statistical_engine import run_linear_mixed_effects_model
    rows = []
    for subject in range(1, 9):
        for time in range(3):
            rows.append({"subject": subject, "time": float(time),
                         "score": subject * 0.3 + time * 1.2 + ((subject + time) % 3) * 0.15})
    result = run_linear_mixed_effects_model(pd.DataFrame(rows), "score", "subject", ["time"], 0.90)
    assert result.metadata["confidence_level"] == pytest.approx(0.90)
    assert "90% CI lower" in result.tables["fixed_effects"].columns
    assert "90% CI upper" in result.tables["fixed_effects"].columns


def test_linear_mixed_effects_model_rejects_invalid_confidence_level():
    from timan_intelligence.core.statistical_engine import run_linear_mixed_effects_model
    frame = pd.DataFrame({"subject": [1,1,2,2,3,3], "time": [0,1,0,1,0,1],
                          "score": [1,2,2,3,3,4]})
    with pytest.raises(ValueError, match="Confidence level"):
        run_linear_mixed_effects_model(frame, "score", "subject", ["time"], 1.0)


def test_linear_mixed_effects_model_returns_residual_and_random_effect_diagnostics():
    from timan_intelligence.core.statistical_engine import run_linear_mixed_effects_model
    rows = []
    for subject in range(1, 13):
        for time in range(4):
            noise = ((subject * 7 + time * 3) % 11 - 5) * 0.07
            rows.append({"subject": f"S{subject}", "time": float(time),
                         "score": subject * 0.35 + 1.8 * time + noise})
    result = run_linear_mixed_effects_model(pd.DataFrame(rows), "score", "subject", ["time"])
    assert {"diagnostic_summary", "residual_diagnostics", "normal_qq", "random_intercepts"}.issubset(result.tables)
    diagnostics = result.tables["diagnostic_summary"]
    assert "Residual normality (Shapiro-Wilk)" in diagnostics["Diagnostic"].tolist()
    assert len(result.tables["residual_diagnostics"]) <= 500
    assert len(result.tables["normal_qq"]) <= 500
    assert len(result.tables["random_intercepts"]) == 12
    assert set(["Fitted value", "Residual", "Standardized residual", "Group"]).issubset(result.tables["residual_diagnostics"].columns)


def test_linear_mixed_effects_model_diagnostics_reports_extreme_residual_count():
    from timan_intelligence.core.statistical_engine import run_linear_mixed_effects_model
    rows = []
    for subject in range(1, 13):
        for time in range(4):
            rows.append({"subject": f"S{subject}", "time": float(time),
                         "score": subject * 0.35 + 1.8 * time + ((subject + time) % 3) * 0.08})
    result = run_linear_mixed_effects_model(pd.DataFrame(rows), "score", "subject", ["time"])
    diag = result.tables["diagnostic_summary"]
    row = diag.loc[diag["Diagnostic"] == "Standardized residuals with absolute value > 3"].iloc[0]
    assert int(row["Statistic"]) >= 0


def test_linear_mixed_effects_model_fits_optional_numeric_random_slope():
    from timan_intelligence.core.statistical_engine import run_linear_mixed_effects_model
    rows = []
    for subject in range(1, 19):
        slope = 0.7 + subject * 0.035
        intercept = subject * 0.25
        for time in range(5):
            noise = ((subject * 3 + time * 5) % 7 - 3) * 0.035
            rows.append({"subject": f"S{subject}", "time": float(time),
                         "score": intercept + slope * time + noise})
    result = run_linear_mixed_effects_model(pd.DataFrame(rows), "score", "subject", ["time"], random_slope_variable="time")
    assert result.status == "success"
    assert result.metadata["random_effect_structure"] == "random_intercept_and_slope"
    assert result.metadata["random_slope_variable"] == "time"
    assert result.metadata["random_slope_variance"] >= 0
    assert {"Group", "Random intercept", "Random slope"}.issubset(result.tables["random_intercepts"].columns)


def test_linear_mixed_effects_model_rejects_categorical_random_slope():
    from timan_intelligence.core.statistical_engine import run_linear_mixed_effects_model
    frame = pd.DataFrame({"subject":[1,1,1,2,2,2,3,3,3],"score":[1,2,3,2,3,4,3,4,5],"visit":[0,1,2,0,1,2,0,1,2],"arm":["A","B","C"]*3})
    with pytest.raises(TypeError, match="numeric"):
        run_linear_mixed_effects_model(frame, "score", "subject", ["visit", "arm"], random_slope_variable="arm")
