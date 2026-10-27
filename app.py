import io

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Timan Intelligence", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    .stApp {background-color: #f7f9fc;}
    .brand {color: #174a7e; font-size: 32px; font-weight: 800;}
    .subtitle {color: #526579; font-size: 15px;}
    div[data-testid="stMetric"] {
        background: white; padding: 14px; border-radius: 10px;
        border: 1px solid #e3eaf2;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

MODULES = {
    "Home": ("Available", "Platform overview and starting point."),
    "Data Management": ("Available", "Upload and inspect CSV or Excel datasets."),
    "Data Quality": ("Available — initial checks", "Review missing values, duplicates and variable structure."),
    "Descriptive Statistics": ("Available — core functions", "Calculate numeric summaries and categorical frequency tables."),
    "Survey Analysis": ("Under development", "Questionnaire analysis, survey design, weights and response patterns."),
    "Statistical Inference": ("Under development", "Confidence intervals, hypothesis tests and statistical association."),
    "Research & Modelling": ("Under development", "Research workflows, regression and advanced statistical models."),
    "MEAL Intelligence": ("Under development", "Indicators, targets, results frameworks, evaluation and accountability."),
    "Business Intelligence": ("Under development", "Business KPIs, sales, costs, profitability and operational performance."),
    "Forecasting & Prediction": ("Under development", "Time-series forecasting and predictive modelling."),
    "Optimisation & Scenarios": ("Under development", "What-if analysis, sensitivity analysis and resource-allocation scenarios."),
    "Visualisations": ("Available — core charts", "Create basic charts from the currently loaded dataset."),
    "AI Analyst": ("Under development", "Natural-language analysis is not connected yet."),
    "Reports & Exports": ("Available — data exports", "Download the current dataset and descriptive statistics."),
    "Settings & Governance": ("Under development", "Authentication, tenant isolation and audit controls are not implemented."),
    "About": ("Available", "Learn about Timan Intelligence and its current limitations."),
}


def status_text(status):
    return f"🟢 {status}" if status.startswith("Available") else f"🟡 {status}"


def numeric_summary(df):
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return pd.DataFrame(
            columns=["variable", "count", "mean", "std", "min", "25%", "50%", "75%", "max"]
        )
    result = numeric.describe().T
    result.index.name = "variable"
    return result.reset_index()


def load_uploaded_file(uploaded_file):
    """Read a supported upload without changing or silently cleaning its contents."""
    file_name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.getvalue()
    if file_name.endswith(".csv"):
        # Try common CSV encodings; pandas' normal comma separator is used.
        last_error = None
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return pd.read_csv(io.BytesIO(raw_bytes), encoding=encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise ValueError(f"Could not decode this CSV file: {last_error}")
    if file_name.endswith(".xlsx"):
        return pd.read_excel(io.BytesIO(raw_bytes), engine="openpyxl")
    raise ValueError("Unsupported file type. Please upload a .csv or .xlsx file.")


def get_dataset():
    df = st.session_state.get("dataset")
    if df is None:
        st.info("Upload a dataset first in **Data Management**.")
        return None
    if df.empty:
        st.warning("The uploaded dataset contains no data rows.")
        return None
    return df


def show_under_development(page, purpose):
    st.title(page)
    st.caption("Module status: 🟡 Under development")
    st.write(purpose)
    st.info("This module is not yet operational. Do not use it as if it provides completed analysis.")


def clear_dataset():
    st.session_state.dataset = None
    st.session_state.dataset_name = None
