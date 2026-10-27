import pandas as pd
import streamlit as st

st.set_page_config(page_title="Timan Intelligence", page_icon="📊", layout="wide")

st.markdown("""
<style>
.stApp {background-color:#f7f9fc;}
.brand {color:#174a7e;font-size:32px;font-weight:800;}
.subtitle {color:#526579;font-size:15px;}
div[data-testid="stMetric"] {background:white;padding:14px;border-radius:10px;border:1px solid #e3eaf2;}
.module-card {background:white;border:1px solid #e3eaf2;border-radius:12px;padding:14px;min-height:145px;margin-bottom:10px;}
</style>
""", unsafe_allow_html=True)

MODULES = {
    "Home": ("Available", "Platform overview and starting point."),
    "Data Management": ("Available", "Upload, inspect and prepare CSV or Excel datasets."),
    "Data Quality": ("Available — initial checks", "Review missing values, duplicates and variable structure."),
    "Descriptive Statistics": ("Available — core functions", "Summaries, frequency distributions and cross-tabulations."),
    "Survey Analysis": ("In development", "Questionnaire analysis, survey design, weights and response patterns."),
    "Statistical Inference": ("In development", "Confidence intervals, hypothesis tests and statistical association."),
    "Research & Modelling": ("In development", "Research workflows, regression and advanced statistical models."),
    "MEAL Intelligence": ("In development", "Indicators, targets, results frameworks, evaluation and accountability."),
    "Business Intelligence": ("In development", "Business KPIs, sales, costs, profitability and operational performance."),
    "Forecasting & Prediction": ("Planned", "Time-series forecasting and predictive modelling."),
    "Optimisation & Scenarios": ("Planned", "What-if analysis, sensitivity analysis and resource-allocation scenarios."),
    "Visualisations": ("Available — core charts", "Explore variables using basic charts."),
    "AI Analyst": ("Planned", "Ask analytical questions in natural language using verified methods."),
    "Reports & Exports": ("Available — data exports", "Export datasets and descriptive statistics."),
    "Settings & Governance": ("Planned", "Future user access, privacy controls and audit records."),
    "About": ("Available", "Learn about Timan Intelligence and its intended use."),
}

def status_text(status):
    if status.startswith("Available"):
        return "🟢 " + status
    if status == "In development":
        return "🟡 " + status
    return "⚪ " + status

def module_intro(title, purpose, status, capabilities):
    st.title(title)
    st.caption("Module status: " + status_text(status))
    st.write(purpose)
    st.subheader("Planned capabilities")
    for item in capabilities:
        st.markdown("- " + item)
    if status.startswith("Available"):
        st.success("Initial functionality is available; scope remains limited to the current prototype.")
    elif status == "In development":
        st.info("This module is part of the platform plan, but its complete workflow is not yet implemented.")
    else:
        st.info("This module is on the roadmap and is not yet operational.")

def current_data():
    df = st.session_state.get("dataset")
    if df is None:
        st.info("Upload a dataset first in **Data Management**.")
        return None
    if df.empty:
        st.warning("The uploaded dataset contains no data rows.")
        return None
    return df

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
    st.sidebar.success("Dataset: " + str(st.session_state.dataset_name or "Uploaded dataset"))
    st.sidebar.caption(f"{loaded.shape[0]:,} rows · {loaded.shape[1]:,} columns")
    if st.sidebar.button("Clear current dataset"):
        st.session_state.dataset = None
        st.session_state.dataset_name = None
        st.rerun()
else:
    st.sidebar.caption("No dataset loaded")

if page == "Home":
    st.markdown('<div class="brand">TIMAN INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">AI-powered statistical analytics by Timan Analytics</div>', unsafe_allow_html=True)
    st.divider()
    st.title("Your data intelligence workspace")
    st.write("A developing platform for turning datasets into statistics, visualisations and evidence for decisions across research, humanitarian work and business.")
    a, b, c = st.columns(3)
    a.metric("Platform", "Analytics")
    b.metric("Current data formats", "CSV / Excel")
