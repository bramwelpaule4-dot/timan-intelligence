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
    if status.startswith("Available"):
        return f"🟢 {status}"
    return f"🟡 {status}"


def get_dataset():
    df = st.session_state.get("dataset")
    if df is None:
        st.info("Upload a dataset first in **Data Management**.")
        return None
    if df.empty:
        st.warning("The uploaded dataset contains no data rows.")
        return None
    return df


def numeric_summary(df):
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        return pd.DataFrame(columns=["variable", "count", "mean", "std", "min", "25%", "50%", "75%", "max"])
    return numeric.describe().T.rename_axis("variable").reset_index()


def show_under_development(page, purpose):
    st.title(page)
    st.caption("Module status: 🟡 Under development")
    st.write(purpose)
    st.info("This module is not yet operational. Do not use it as if it provides completed analysis.")


if "dataset" not in st.session_state:
    st.session_state.dataset = None
if "dataset_name" not in st.session_state:
    st.session_state.dataset_name = None

st.sidebar.markdown("## 🔷 TIMAN")
st.sidebar.caption("INTELLIGENCE")
st.sidebar.divider()
page = st.sidebar.radio("NAVIGATION", list(MODULES.keys()))
st.sidebar.divider()
st.sidebar.caption("Turning Data into Insights for Informed Decisions.")

if st.session_state.dataset is not None:
    loaded = st.session_state.dataset
    st.sidebar.success(f"Dataset: {st.session_state.dataset_name or 'Uploaded dataset'}")
    st.sidebar.caption(f"{loaded.shape[0]:,} rows · {loaded.shape[1]:,} columns")
    if st.sidebar.button("Clear current dataset"):
        st.session_state.dataset = None
        st.session_state.dataset_name = None
        st.session_state.pop("dataset_uploader", None)
        st.rerun()
else:
    st.sidebar.caption("No dataset loaded")
