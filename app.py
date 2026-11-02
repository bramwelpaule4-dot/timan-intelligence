import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from timan_intelligence.config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_ORGANISATION,
    APP_TAGLINE,
    APP_VERSION,
    SHORT_DESCRIPTION,
)
from timan_intelligence.config.branding import PLATFORM_LABEL, SIDEBAR_FOOTER
from timan_intelligence.monitoring.dashboard import render_project_status_dashboard


# ============================================================
# PAGE CONFIGURATION AND BRANDING
# ============================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📊",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background-color: #f7f9fc;
    }
    .brand {
        color: #174a7e;
        font-size: 32px;
        font-weight: 800;
    }
    .subtitle {
        color: #526579;
        font-size: 15px;
    }
    div[data-testid="stMetric"] {
        background: white;
        padding: 14px;
        border-radius: 10px;
        border: 1px solid #e3eaf2;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# MODULE REGISTRY
# ============================================================

MODULES = {
    "Home": (
        "Available",
        "Platform overview and starting point.",
    ),
    "Data Management": (
        "Available",
        "Upload, select, preview and inspect datasets.",
    ),
    "Data Quality": (
        "Available — initial checks",
        "Review missing values, duplicates and variable structure.",
    ),
    "Descriptive Statistics": (
        "Available — core functions",
        "Calculate numeric summaries and categorical frequencies.",
    ),
    "Survey Analysis": (
        "Under development",
        "Questionnaire analysis, survey design, weights and response patterns.",
    ),
    "Statistical Inference": (
        "Under development",
        "Confidence intervals, hypothesis tests and statistical association.",
    ),
    "Research & Modelling": (
        "Under development",
        "Research workflows, regression and advanced statistical models.",
    ),
    "MEAL Intelligence": (
        "Under development",
        "Indicators, targets, results frameworks, evaluation and accountability.",
    ),
    "Business Intelligence": (
        "Under development",
