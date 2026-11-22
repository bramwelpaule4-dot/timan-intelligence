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
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.email_verification import verify_email_token
from timan_intelligence.security.auth import is_authenticated, logout
from timan_intelligence.security.auth_ui import render_authentication
from timan_intelligence.security.developer_diagnostics import (
    render_development_diagnostics,
)
from timan_intelligence.security.developer_diagnostics import (
    render_developer_dashboard_access,
)
from timan_intelligence.security.federated_login import process_federated_login_callback
from timan_intelligence.security.password_change_ui import render_password_change
from timan_intelligence.security.contact_methods_ui import render_contact_methods
from timan_intelligence.security.totp_management_ui import render_totp_management
from timan_intelligence.organisations.service import list_user_organisations
from timan_intelligence.entitlements.subscription_ui import render_subscription_page
from timan_intelligence.entitlements.subscription_admin_ui import render_subscription_administration
from timan_intelligence.administration.user_admin_ui import render_user_administration
from timan_intelligence.services.analysis_service import (
    run_survey_profile,
    run_weighted_frequency_service,
    run_weighted_numeric_summary_service,
    run_stratified_weighted_mean_service,
    run_stratified_weighted_frequency_service,
    run_cluster_weighted_mean_service,
    run_cluster_weighted_frequency_service,
    run_two_stage_survey_design_inspection_service,
    run_two_stage_survey_total_service,
    run_categorical_comparison,
    run_numeric_group_comparison_service,
    run_numeric_association_service,
    run_simple_linear_regression_service,
    run_multiple_linear_regression_service,
    run_binary_logistic_regression_service,
    run_ordinal_logistic_regression_service,
    run_poisson_regression_service,
    run_negative_binomial_regression_service,
    run_kaplan_meier_service,
    run_cox_survival_service,
    run_multinomial_logistic_regression_service,
    recommend_categorical_outcome_model_service,
    run_regression_diagnostics_service,
)
from timan_intelligence.entitlements.subscriptions import process_due_subscriptions
from timan_intelligence.entitlements.service import (
    DatasetLimitExceeded,
    UsageLimitExceeded,
    consume_monthly_usage,
    get_effective_entitlements,
    get_monthly_usage,
    validate_dataset_limits,
)


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
    :root {
        --timan-navy: #173B67;
        --timan-blue: #2586C7;
        --timan-red: #D94A45;
        --timan-teal: #169B78;
        --timan-gold: #F2B544;
        --timan-bg: #F3F6FA;
        --timan-border: #DCE5EF;
        --timan-text: #24364B;
        --timan-muted: #64758B;
    }

    .stApp {
        background:
            radial-gradient(circle at 92% 0%, rgba(37, 134, 199, .08), transparent 26rem),
            var(--timan-bg);
        color: var(--timan-text);
    }

    /* Consistent typography and page rhythm */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    h1, h2, h3 {
        color: var(--timan-navy);
        letter-spacing: -0.025em;
    }
    h1 {
        font-weight: 800;
        padding-bottom: .35rem;
        border-bottom: 3px solid rgba(37, 134, 199, .22);
    }
    h2, h3 {
        font-weight: 700;
    }
    .brand {
        color: var(--timan-navy);
        font-size: 32px;
        font-weight: 800;
    }
    .subtitle {
        color: var(--timan-muted);
        font-size: 15px;
    }
    p, li, label, [data-testid="stCaptionContainer"] {
        color: var(--timan-text);
    }
    [data-testid="stCaptionContainer"] {
        color: var(--timan-muted);
    }

    /* Sidebar: branded navy surface with clear navigation contrast */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #173B67 0%, #102D50 100%);
        border-right: 1px solid rgba(255,255,255,.10);
    }
    section[data-testid="stSidebar"] > div {
        background: transparent;
    }
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #F3F7FC;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #C2D3E5;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,.20);
    }
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        color: #D9E7F5;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        border-radius: 9px;
        padding: 7px 10px;
        transition: background .18s ease;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(255,255,255,.12);
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
        background: rgba(37,134,199,.32);
        border-left: 3px solid #F2B544;
    }
    section[data-testid="stSidebar"] [data-testid="stImage"] img {
        border-radius: 12px;
    }

    /* Compact, consistent navigation hierarchy */
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,.13);
        border-radius: 10px;
        background: rgba(255,255,255,.035);
        margin: 0 0 8px 0;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
        color: #DCEAF7;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: .105em;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] details {
        border: 0;
    }
    section[data-testid="stSidebar"] .stButton > button {
        min-height: 2.25rem;
        padding: .38rem .65rem;
        border-radius: 7px;
        border: 1px solid transparent;
        background: transparent;
        color: #E7F0F8;
        font-size: .84rem;
        font-weight: 550;
        text-align: left;
        justify-content: flex-start;
        box-shadow: none;
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,.10);
        border-color: rgba(255,255,255,.12);
        color: #FFFFFF;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
        background: rgba(37,134,199,.30);
        border-color: rgba(117,196,242,.35);
        border-left: 3px solid #F2B544;
        color: #FFFFFF;
        font-weight: 750;
    }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
        background: rgba(37,134,199,.40);
        color: #FFFFFF;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
        color: #BFD3E6;
    }

    /* Buttons and interactive controls */
    .stButton > button, .stDownloadButton > button {
        border-radius: 9px;
        border: 1px solid var(--timan-blue);
        font-weight: 650;
        transition: all .18s ease;
    }
    .stButton > button[kind="primary"],
    .stDownloadButton > button[kind="primary"] {
        background: var(--timan-blue);
        border-color: var(--timan-blue);
        color: #FFFFFF;
    }
    .stButton > button[kind="primary"]:hover,
    .stDownloadButton > button[kind="primary"]:hover {
        background: var(--timan-navy);
        border-color: var(--timan-navy);
        color: #FFFFFF;
    }
    .stButton > button:not([kind="primary"]):hover,
    .stDownloadButton > button:not([kind="primary"]):hover {
        border-color: var(--timan-blue);
        color: var(--timan-navy);
        background: rgba(37,134,199,.07);
    }
    input:focus, textarea:focus, [data-baseweb="select"]:focus-within {
        border-color: var(--timan-blue) !important;
        box-shadow: 0 0 0 1px var(--timan-blue) !important;
    }
    [role="tab"][aria-selected="true"] {
        color: var(--timan-navy) !important;
        border-bottom-color: var(--timan-blue) !important;
        font-weight: 700;
    }

    /* Dashboard metrics and content surfaces */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #FFFFFF 0%, #F8FBFE 100%);
        padding: 16px;
        border-radius: 12px;
        border: 1px solid var(--timan-border);
        border-top: 3px solid var(--timan-blue);
        box-shadow: 0 3px 12px rgba(23,59,103,.045);
    }
    div[data-testid="stMetric"] label {
        color: var(--timan-muted);
        font-weight: 600;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: var(--timan-navy);
        font-weight: 800;
    }
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {
        border: 1px solid var(--timan-border);
        border-radius: 10px;
        overflow: hidden;
    }
    div[data-testid="stAlert"] {
        border-radius: 10px;
    }
    div[data-testid="stProgressBar"] > div > div {
        background: var(--timan-teal);
    }
    div[data-testid="stExpander"] {
        border: 1px solid var(--timan-border);
        border-radius: 10px;
        background: rgba(255,255,255,.72);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 9px 14px;
    }

    /* Keep Streamlit's native focus indicators visible */
    button:focus-visible, a:focus-visible, input:focus-visible {
        outline: 2px solid var(--timan-gold) !important;
        outline-offset: 2px !important;
    }

    /* Branded landing-page header */
    .home-hero {
        background: linear-gradient(118deg, #FFFFFF 0%, #F0F6FC 72%, #E7F1FA 100%);
        border: 1px solid var(--timan-border);
        border-left: 5px solid var(--timan-blue);
        border-radius: 16px;
        padding: 1.35rem 1.6rem;
        margin: .2rem 0 1.25rem 0;
        box-shadow: 0 8px 24px rgba(23,59,103,.055);
    }
    .home-eyebrow {
        color: var(--timan-blue);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .13em;
        text-transform: uppercase;
        margin-bottom: .45rem;
    }
    .home-heading {
        color: var(--timan-navy);
        font-size: clamp(1.8rem, 3vw, 2.55rem);
        font-weight: 850;
        line-height: 1.08;
        letter-spacing: -.04em;
        margin: 0 0 .55rem 0;
    }
    .home-tagline {
        color: var(--timan-muted);
        font-size: 1rem;
        line-height: 1.55;
        margin: 0;
        max-width: 48rem;
    }
    .home-description {
        color: var(--timan-text);
        font-size: 1rem;
        line-height: 1.7;
        max-width: 70rem;
        margin: .8rem 0 1.35rem 0;
    }
    .section-kicker {
        color: var(--timan-blue);
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
        margin-bottom: .55rem;
    }
    .home-hero {
        padding: 1.8rem 2rem 1.65rem;
        border-left: 0;
        border-top: 4px solid var(--timan-blue);
        margin-bottom: 1.65rem;
    }
    .product-lockup {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .product-symbol, .sidebar-symbol {
        display: flex;
        align-items: flex-end;
        justify-content: center;
        gap: 3px;
        width: 43px;
        height: 43px;
        padding: 8px;
        border: 1px solid rgba(37,134,199,.22);
        border-radius: 11px;
        background: #FFFFFF;
    }
    .product-symbol span, .sidebar-symbol span {
        display: block;
        width: 6px;
        border-radius: 3px 3px 1px 1px;
        background: #2586C7;
    }
    .product-symbol span:nth-child(1), .sidebar-symbol span:nth-child(1) {
        height: 12px;
        background: #2586C7;
    }
    .product-symbol span:nth-child(2), .sidebar-symbol span:nth-child(2) {
        height: 21px;
        background: #169B78;
    }
    .product-symbol span:nth-child(3), .sidebar-symbol span:nth-child(3) {
        height: 16px;
        background: #B24D9A;
    }
    .home-heading {
        font-size: 1.65rem;
        line-height: 1;
        margin: 0 0 .3rem;
        letter-spacing: -.035em;
    }
    .wordmark-accent {
        color: var(--timan-blue);
    }
    .home-eyebrow {
        margin: 0;
        font-size: 9px;
        letter-spacing: .15em;
    }
    .product-byline {
        color: var(--timan-muted);
        font-size: .78rem;
        margin-top: .22rem;
    }
    .hero-divider {
        height: 1px;
        background: var(--timan-border);
        margin: 1.25rem 0 1.15rem;
    }
    .hero-statement {
        color: var(--timan-navy);
        font-size: clamp(1.75rem, 3.4vw, 2.55rem);
        line-height: 1.12;
        font-weight: 800;
        letter-spacing: -.045em;
        margin: 0 0 .65rem;
        border: 0;
        padding: 0;
    }
    .home-description {
        color: var(--timan-muted);
        font-size: 1rem;
        line-height: 1.65;
        max-width: 57rem;
        margin: 0;
    }
    .feature-card {
        min-height: 170px;
        height: 100%;
        box-sizing: border-box;
        padding: 1.05rem 1rem 1.1rem;
        background: #FFFFFF;
        border: 1px solid var(--timan-border);
        border-top: 3px solid var(--timan-blue);
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(23,59,103,.045);
    }
    .feature-blue { border-top-color: #2586C7; }
    .feature-teal { border-top-color: #169B78; }
    .feature-gold { border-top-color: #D9A02F; }
    .feature-red { border-top-color: #B24D75; }
    .feature-card-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
    }
    .feature-symbol {
        color: var(--timan-blue);
        font-size: 1.45rem;
        font-weight: 750;
        line-height: 1;
    }
    .feature-number {
        color: #91A2B5;
        font-size: .7rem;
        font-weight: 750;
        letter-spacing: .1em;
    }
    .feature-title {
        color: var(--timan-navy);
        font-size: .98rem;
        font-weight: 750;
        line-height: 1.25;
        margin-bottom: .45rem;
    }
    .feature-description {
        color: var(--timan-muted);
        font-size: .83rem;
        line-height: 1.5;
    }
    .workspace-kicker {
        margin-top: 1.8rem;
    }
    .sidebar-brand {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 20px 4px 18px;
    }
    .sidebar-symbol {
        width: 38px;
        height: 38px;
        margin-bottom: 10px;
        background: rgba(255,255,255,.98);
    }
    .sidebar-wordmark {
        color: #FFFFFF;
        font-size: 25px;
        font-weight: 850;
        letter-spacing: -.045em;
        line-height: 1.1;
    }
    .sidebar-wordmark span {
        color: #75C4F2 !important;
    }
    .sidebar-platform-label {
        color: #D7E6F4;
        font-size: 9px;
        font-weight: 750;
        letter-spacing: .11em;
        margin-top: 7px;
    }
    .sidebar-byline {
        color: #C2D3E5;
        font-size: 11px;
        margin-top: 7px;
    }

    @media (max-width: 768px) {
        .home-hero { padding: 1.35rem 1.2rem; }
        .feature-card { min-height: 145px; }
        .block-container {
        .block-container {
            padding-top: 1.2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# PUBLIC DEVELOPMENT MODE
# ============================================================

# Authentication is intentionally paused while core statistical modules
# are developed. Re-enable this switch only after identity and account
# recovery have been re-tested end-to-end.
PUBLIC_ACCESS_MODE = True
PUBLIC_PLAN_LIMITS = {
    "max_dataset_rows": 10_000,
    "max_upload_size_mb": 25,
    "monthly_analyses": 100,
    "monthly_exports": 10,
}


def consume_public_usage(metric: str) -> int:
    """Apply provisional per-browser-session limits in public preview mode."""
    if metric not in {"monthly_analyses", "monthly_exports"}:
        raise ValueError("Unsupported public preview usage metric.")
    key = f"timanstat_public_usage_{metric}"
    used = int(st.session_state.get(key, 0))
    limit = PUBLIC_PLAN_LIMITS[metric]
    if used >= limit:
        raise UsageLimitExceeded(
            f"The public preview allows {limit} {metric.replace('_', ' ')} "
            "per browser session."
        )
    used += 1
    st.session_state[key] = used
    return used


def validate_current_dataset_limits(
    *, file_size_bytes: int | None = None, row_count: int | None = None
) -> None:
    """Apply Free-plan-sized upload safeguards without requiring an account."""
    if not PUBLIC_ACCESS_MODE:
        user_id = st.session_state.get("user_id")
        if not isinstance(user_id, str) or not user_id.strip():
            raise RuntimeError(
                "Your authenticated account could not be verified. Please sign in again."
            )
        validate_dataset_limits(
            user_id=user_id,
            file_size_bytes=file_size_bytes,
            row_count=row_count,
            organisation_id=st.session_state.get("active_organisation_id"),
        )
        return

    if file_size_bytes is not None:
        if file_size_bytes > PUBLIC_PLAN_LIMITS["max_upload_size_mb"] * 1024 * 1024:
            raise DatasetLimitExceeded(
                "The public preview allows uploads up to 25 MB."
            )
    if row_count is not None and row_count > PUBLIC_PLAN_LIMITS["max_dataset_rows"]:
        raise DatasetLimitExceeded(
            "The public preview allows datasets up to 10,000 rows."
        )


# Core statistical tools are session-based and do not require the identity
# database. Initialise it opportunistically for development monitoring, but
# never block public statistical work if the database is unavailable.
PUBLIC_DATABASE_AVAILABLE = False
if PUBLIC_ACCESS_MODE:
    try:
        initialise_database()
        PUBLIC_DATABASE_AVAILABLE = True
    except Exception:
        PUBLIC_DATABASE_AVAILABLE = False

# Authentication, registration, subscriptions and account security remain
# in the repository but are not exposed in this public preview.
if not PUBLIC_ACCESS_MODE:
    try:
        initialise_database()
        process_due_subscriptions()
    except Exception:
        st.error(
            "TimanStat could not connect to its database. "
            "Please try again later or contact the platform administrator."
        )
        render_development_diagnostics()
        st.stop()

    if st.session_state.get("pending_authentication") is not True:
        process_federated_login_callback()

    verification_token = st.query_params.get("verify_email")
    if verification_token is not None:
        try:
            verification_succeeded = verify_email_token(verification_token)
        except Exception:
            verification_succeeded = False
        if verification_succeeded:
            st.success(
                "Your email address has been verified. "
                "You can now sign in to TimanStat."
            )
        else:
            st.error(
                "This verification link is invalid, expired or has already "
                "been used. Please request assistance from the platform administrator."
            )
        if "verify_email" in st.query_params:
            del st.query_params["verify_email"]

    password_reset_requested = bool(st.query_params.get("reset_password"))
    if password_reset_requested and is_authenticated():
        logout()
    if not is_authenticated() or password_reset_requested:
        render_authentication()
        st.stop()
else:
    password_reset_requested = False


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
        "Available — profiling and Likert item analysis",
        "Inspect questionnaire structure, response patterns and ordered Likert items.",
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
        "Business KPIs, sales, costs, profitability and operational performance.",
    ),
    "Forecasting & Prediction": (
        "Under development",
        "Time-series forecasting and predictive modelling.",
    ),
    "Optimisation & Scenarios": (
        "Under development",
        "What-if analysis, sensitivity analysis and resource-allocation scenarios.",
    ),
    "Visualisations": (
        "Available — core charts",
        "Create basic charts from the currently loaded dataset.",
    ),
    "AI Analyst": (
        "Under development",
        "Natural-language analysis is not connected yet.",
    ),
    "Reports & Exports": (
        "Available — data exports",
        "Download the current dataset and available descriptive outputs.",
    ),
    "Subscription Administration": (
        "Available — platform administrators only",
        "Assign subscription plans to individual accounts and organisations.",
    ),
    "User Administration": (
        "Available — platform administrators only",
        "Review accounts, manage access and inspect administrative audit history.",
    ),
    "Subscription": (
        "Available",
        "Review your active plan, usage allowances and subscription history.",
    ),
    "Account & Security": (
        "Available",
        "Manage your account password and security settings.",
    ),
    "Settings & Governance": (
        "Under development",
        "Account authentication and role-based access are implemented; "
        "tenant administration and audit controls remain under development.",
    ),
    "Developer Dashboard": (
        "Developer only",
        "Monitor module availability, implementation, verification and project progress.",
    ),
    "About": (
        "Available",
        "Learn about TimanStat and its current capabilities.",
    ),
}


def status_text(status):
    """Format module availability consistently."""
    if status.startswith("Available"):
        return f"🟢 {status}"
    return f"🟡 {status}"


# ============================================================
# SESSION STATE
# ============================================================

if "dataset" not in st.session_state:
    st.session_state.dataset = None

if "dataset_name" not in st.session_state:
    st.session_state.dataset_name = None

if "dataset_source_key" not in st.session_state:
    st.session_state.dataset_source_key = None

if "navigation_page" not in st.session_state:
    st.session_state.navigation_page = "Home"


def clear_dataset():
    """Clear the currently loaded dataset."""
    st.session_state.dataset = None
    st.session_state.dataset_name = None
    st.session_state.dataset_source_key = None
    st.session_state.pop("dataset_uploader", None)


def go_to_data_management():
    """Navigate to Data Management using a Streamlit callback."""
    st.session_state.navigation_page = "Data Management"


# ============================================================
# DATA LOADING AND STATISTICAL HELPERS
# ============================================================

def get_upload_id(uploaded_file):
    """Create a fingerprint for an uploaded file."""
    return hashlib.sha256(
        uploaded_file.getvalue()
    ).hexdigest()


def load_uploaded_file(uploaded_file, sheet_name=None):
    """
    Load a CSV file or a specifically selected Excel worksheet.

    Excel imports require an explicit worksheet selection.
    The source data is not silently cleaned or recoded.
    """
    file_name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.getvalue()

    if file_name.endswith(".csv"):
        last_error = None

        for encoding in (
            "utf-8-sig",
            "utf-8",
            "cp1252",
            "latin-1",
        ):
            try:
                return pd.read_csv(
                    io.BytesIO(raw_bytes),
                    encoding=encoding,
                )
            except UnicodeDecodeError as exc:
                last_error = exc

        raise ValueError(
            f"Could not decode this CSV file: {last_error}"
        )

    if file_name.endswith(".xlsx"):
        if sheet_name is None:
            raise ValueError(
                "Select an Excel worksheet before importing."
            )

        return pd.read_excel(
            io.BytesIO(raw_bytes),
            sheet_name=sheet_name,
            engine="openpyxl",
        )

    raise ValueError(
        "Unsupported file type. Upload a CSV or .xlsx workbook."
    )


def numeric_summary(df):
    """Calculate standard descriptive statistics for numeric columns."""
    numeric = df.select_dtypes(include="number")

    if numeric.empty:
        return pd.DataFrame(
            columns=[
                "variable",
                "count",
                "mean",
                "std",
                "min",
                "25%",
                "50%",
                "75%",
                "max",
            ]
        )

    result = numeric.describe().T
    result.index.name = "variable"

    return result.reset_index()


def variable_quality_profile(df):
    """Create a detailed variable-level data-quality summary."""
    row_count = len(df)
    records = []

    for col in df.columns:
        series = df[col]
        missing_count = int(series.isna().sum())
        blank_count = 0

        if (
            pd.api.types.is_object_dtype(series.dtype)
            or pd.api.types.is_string_dtype(series.dtype)
        ):
            text_values = series.dropna().astype(str)
            blank_count = int(text_values.str.strip().eq("").sum())

        total_missing_like = missing_count + blank_count
        non_missing = row_count - missing_count
        unique_count = int(series.nunique(dropna=True))

        records.append(
            {
                "Variable": str(col),
                "Data type": str(series.dtype),
                "Records": row_count,
                "Missing values": missing_count,
                "Missing (%)": round(missing_count / row_count * 100, 2)
                if row_count else 0.0,
                "Blank strings": blank_count,
                "Missing/blank (%)": round(
                    total_missing_like / row_count * 100, 2
                ) if row_count else 0.0,
                "Non-missing values": non_missing,
                "Unique values": unique_count,
                "Unique (%)": round(
                    unique_count / non_missing * 100, 2
                ) if non_missing else 0.0,
                "Constant column": "Yes"
                if unique_count <= 1 and row_count > 0 else "No",
            }
        )

    return pd.DataFrame(records)


def numeric_outlier_profile(df):
    """Flag potential IQR outliers without changing source values."""
    numeric = df.select_dtypes(include="number")
    records = []

    for col in numeric.columns:
        values = numeric[col].dropna()
        if values.empty:
            continue

        q1 = values.quantile(0.25)
        q3 = values.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = values[(values < lower) | (values > upper)]

        records.append(
            {
                "Variable": str(col),
                "Valid values": int(values.count()),
                "Q1": q1,
                "Q3": q3,
                "IQR": iqr,
                "Lower fence": lower,
                "Upper fence": upper,
                "Potential outliers": int(outliers.count()),
                "Potential outliers (%)": round(
                    outliers.count() / values.count() * 100, 2
                ) if values.count() else 0.0,
            }
        )

    return pd.DataFrame(records)



def get_active_organisation_id():
    """Return the organisation selected as the current billing context."""
    organisation_id = st.session_state.get("active_organisation_id")
    return organisation_id if isinstance(organisation_id, str) and organisation_id else None


def quota_download_button(label, **kwargs):
    """Require and consume one monthly export allowance before enabling a download."""
    export_key = kwargs.get("key")
    if not isinstance(export_key, str) or not export_key:
        raise ValueError("Quota-controlled downloads require a stable key.")

    ready_key = f"timanstat_export_ready_{export_key}"
    prepare_key = f"timanstat_prepare_export_{export_key}"

    if st.button(f"Prepare export: {label}", key=prepare_key):
        try:
            if PUBLIC_ACCESS_MODE:
                consume_public_usage("monthly_exports")
            else:
                user_id = st.session_state.get("user_id")
                if not isinstance(user_id, str) or not user_id.strip():
                    raise RuntimeError(
                        "Your authenticated account could not be verified. Please sign in again."
                    )
                consume_monthly_usage(
                    "monthly_exports",
                    user_id=user_id,
                    organisation_id=get_active_organisation_id(),
                )
        except (UsageLimitExceeded, RuntimeError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("The export allowance could not be verified. No export was prepared.")
        else:
            st.session_state[ready_key] = True

    if st.session_state.get(ready_key):
        downloaded = st.download_button(label, **kwargs)
        if downloaded:
            st.session_state[ready_key] = False


def _dataset_analysis_key(df):
    """Create a stable session key for the currently loaded dataset."""
    row_hashes = pd.util.hash_pandas_object(df, index=True).values.tobytes()
    column_names = repr(tuple(str(column) for column in df.columns)).encode("utf-8")
    return hashlib.sha256(column_names + row_hashes).hexdigest()


def get_dataset():
    """Return the active dataset, with appropriate guidance if absent."""
    df = st.session_state.dataset

    if df is None:
        st.info(
            "Upload and import a dataset first in Data Management."
        )
        return None

    if df.empty:
        st.warning(
            "The imported worksheet contains no data rows."
        )
        return None

    return df



def render_categorical_comparison(df):
    """Render guided cross-tabulation and association analysis."""
    st.subheader("Compare categorical variables")
    st.write(
        "Examine how the distribution of one categorical variable differs "
        "across groups. TimanStat selects an appropriate association test "
        "when the data support one; you do not need to choose the test."
    )

    candidates = []
    for column in df.columns:
        series = df[column]
        unique_count = int(series.nunique(dropna=True))
        if 2 <= unique_count <= 50:
            is_text = (
                pd.api.types.is_object_dtype(series.dtype)
                or pd.api.types.is_string_dtype(series.dtype)
                or pd.api.types.is_bool_dtype(series.dtype)
                or isinstance(series.dtype, pd.CategoricalDtype)
            )
            is_low_cardinality_integer = (
                pd.api.types.is_integer_dtype(series.dtype)
                and unique_count <= 10
            )
            if is_text or is_low_cardinality_integer:
                candidates.append(column)

    if len(candidates) < 2:
        st.info(
            "At least two suitable categorical variables are needed. "
            "Text/category variables and low-cardinality integer codes are "
            "considered. Confirm any numeric codes against the data dictionary."
        )
        return

    left, right = st.columns(2)
    row_variable = left.selectbox(
        "Grouping variable (rows)",
        candidates,
        key="categorical_comparison_row",
        help="The groups you want to compare, such as sex, location or programme.",
    )
    outcome_options = [column for column in candidates if column != row_variable]
    column_variable = right.selectbox(
        "Outcome variable (columns)",
        outcome_options,
        key="categorical_comparison_column",
        help="The categorical response or characteristic to compare between groups.",
    )

    st.caption(
        "The analysis uses records with valid values for both variables. "
        "Blank and missing values are excluded and reported. Variables with "
        "more than 50 categories are not offered because they may be IDs or free text."
    )

    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_categorical_comparison_{dataset_key}"
    if st.button(
        "Run categorical comparison",
        type="primary",
        key="run_categorical_comparison",
    ):
        try:
            comparison = run_categorical_comparison(
                df,
                str(row_variable),
                str(column_variable),
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "The comparison could not be completed. No inferential result "
                "has been reported."
            )
        else:
            st.session_state[result_key] = {
                "row_variable": row_variable,
                "column_variable": column_variable,
                "result": comparison,
            }

    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Choose the two variables, then run the comparison to view results.")
        return
    if saved["row_variable"] != row_variable or saved["column_variable"] != column_variable:
        st.info("Run the comparison again to apply the changed variable selection.")
        return

    result = saved["result"]
    metadata = result.metadata
    st.markdown("#### Comparison summary")
    metrics = st.columns(4)
    metrics[0].metric("Valid records", f"{metadata['valid_n']:,}")
    metrics[1].metric("Excluded records", f"{metadata['excluded_n']:,}")
    metrics[2].metric("Association test", metadata["test"])
    metrics[3].metric(
        "P-value",
        f"{metadata['p_value']:.4g}" if metadata.get("p_value") is not None else "Not calculated",
    )

    if metadata.get("cramers_v") is not None:
        st.caption(f"Cramér's V (effect-size estimate): {metadata['cramers_v']:.3f}")
    if metadata.get("minimum_expected_count") is not None:
        st.caption(
            "Minimum expected cell count: "
            f"{metadata['minimum_expected_count']:.2f} · "
            f"Expected cells below 5: {metadata['expected_cells_below_5']}"
        )

    counts_tab, row_tab, column_tab = st.tabs(
        ["Observed counts", "Row percentages", "Column percentages"]
    )
    with counts_tab:
        st.dataframe(result.tables["observed_counts"], use_container_width=True)
        st.caption("Counts show complete records in each group/outcome combination.")
    with row_tab:
        st.dataframe(result.tables["row_percentages"], use_container_width=True)
        st.caption(
            "Row percentages use each grouping-variable category as the denominator. "
            "Each row totals 100%."
        )
    with column_tab:
        st.dataframe(result.tables["column_percentages"], use_container_width=True)
        st.caption(
            "Column percentages use each outcome category as the denominator. "
            "Each outcome column totals 100%."
        )

    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)

def render_numeric_group_comparison(df):
    """Render guided comparison of a numeric outcome across independent groups."""
    st.subheader("Compare a numeric outcome across groups")
    st.write(
        "Compare a measured numeric outcome, such as income, age, expenditure "
        "or test score, across categories such as location, sex or programme. "
        "TimanStat selects Welch's t-test for two groups or Welch's one-way "
        "ANOVA for three or more groups when the data support inference."
    )

    group_candidates = []
    for column in df.columns:
        series = df[column]
        unique_count = int(series.nunique(dropna=True))
        if not 2 <= unique_count <= 50:
            continue
        is_text_or_category = (
            pd.api.types.is_object_dtype(series.dtype)
            or pd.api.types.is_string_dtype(series.dtype)
            or pd.api.types.is_bool_dtype(series.dtype)
            or isinstance(series.dtype, pd.CategoricalDtype)
        )
        is_low_cardinality_integer = (
            pd.api.types.is_integer_dtype(series.dtype)
            and unique_count <= 10
        )
        if is_text_or_category or is_low_cardinality_integer:
            group_candidates.append(column)

    numeric_candidates = [
        column for column in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[column].dtype)
    ]

    if not group_candidates or not numeric_candidates:
        st.info(
            "This comparison needs at least one categorical grouping variable "
            "and one numeric outcome variable. Numeric text columns are not "
            "automatically converted; check the imported variable types."
        )
        return

    left, right = st.columns(2)
    group_variable = left.selectbox(
        "Grouping variable",
        group_candidates,
        key="numeric_comparison_group",
        help="A category defining independent groups, such as location or programme.",
    )
    outcome_variable = right.selectbox(
        "Numeric outcome",
        numeric_candidates,
        key="numeric_comparison_outcome",
        help="A measured numeric variable whose distribution or mean you want to compare.",
    )

    st.caption(
        "Blank group labels and missing or non-finite outcome values are "
        "excluded and reported. Group codes should be checked against the "
        "dataset's data dictionary. The analysis is unweighted and does not "
        "adjust for complex survey sampling."
    )

    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_numeric_group_comparison_{dataset_key}"
    if st.button(
        "Run numeric group comparison",
        type="primary",
        key="run_numeric_group_comparison",
    ):
        try:
            comparison = run_numeric_group_comparison_service(
                df,
                str(group_variable),
                str(outcome_variable),
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "The numeric comparison could not be completed. "
                "No inferential result has been reported."
            )
        else:
            st.session_state[result_key] = {
                "group_variable": group_variable,
                "outcome_variable": outcome_variable,
                "result": comparison,
            }

    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Choose the grouping and outcome variables, then run the comparison.")
        return
    if (
        saved["group_variable"] != group_variable
        or saved["outcome_variable"] != outcome_variable
    ):
        st.info("Run the comparison again to apply the changed variable selection.")
        return

    result = saved["result"]
    metadata = result.metadata
    st.markdown("#### Comparison summary")
    metrics = st.columns(4)
    metrics[0].metric("Valid records", f"{metadata['valid_n']:,}")
    metrics[1].metric("Excluded records", f"{metadata['excluded_n']:,}")
    metrics[2].metric("Selected test", metadata["test"])
    metrics[3].metric(
        "P-value",
        f"{metadata['p_value']:.4g}"
        if metadata.get("p_value") is not None else "Not calculated",
    )

    st.dataframe(result.tables["group_summaries"], use_container_width=True)
    st.caption(
        "Group summaries include sample size, mean, standard deviation, "
        "median, quartiles and observed range."
    )

    if metadata.get("mean_difference") is not None:
        ci = metadata.get("confidence_interval_95")
        if ci is not None:
            st.caption(
                f"Mean difference ({metadata['group_labels'][1]} minus "
                f"{metadata['group_labels'][0]}): "
                f"{metadata['mean_difference']:.3g}; 95% confidence interval "
                f"[{ci[0]:.3g}, {ci[1]:.3g}]."
            )
    elif metadata.get("degrees_freedom"):
        df_values = metadata["degrees_freedom"]
        st.caption(
            "Welch ANOVA degrees of freedom: "
            f"{df_values['numerator']:.3g} (numerator), "
            f"{df_values['denominator']:.3g} (denominator)."
        )

    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    if metadata.get("test") == "Welch's one-way ANOVA":
        st.info(
            "Welch ANOVA is an omnibus test. A statistically significant result "
            "indicates that not all group means are equal; it does not identify "
            "which groups differ. Post-hoc pairwise comparisons are not yet available."
        )
    st.caption(
        "A p-value is not a measure of the size or practical importance of a difference."
    )
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)



def render_numeric_association(df):
    """Render guided correlation analysis for two numeric variables."""
    st.subheader("Explore the relationship between two numeric variables")
    st.write(
        "Examine whether two measured variables move together, for example "
        "household income and expenditure, training hours and assessment score, "
        "or age and service utilisation. TimanStat reports both Pearson and "
        "Spearman correlations so users do not need to select a coefficient "
        "without first understanding the difference."
    )
    numeric_candidates = [
        column for column in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[column].dtype)
    ]
    if len(numeric_candidates) < 2:
        st.info(
            "This analysis requires at least two numeric variables. "
            "Check whether numeric values were imported as text."
        )
        return

    left, right = st.columns(2)
    first_variable = left.selectbox(
        "First numeric variable",
        numeric_candidates,
        key="numeric_association_first",
        help="Select the first measured variable.",
    )
    second_options = [item for item in numeric_candidates if item != first_variable]
    second_variable = right.selectbox(
        "Second numeric variable",
        second_options,
        key="numeric_association_second",
        help="Select a different measured variable.",
    )
    st.caption(
        "At least three complete finite pairs are required. Missing and "
        "non-finite pairs are excluded and counted. Text-coded numbers must "
        "be converted during data preparation; TimanStat will not guess their meaning."
    )

    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_numeric_association_{dataset_key}"
    if st.button(
        "Analyse numeric relationship",
        type="primary",
        key="run_numeric_association",
    ):
        try:
            association = run_numeric_association_service(
                df,
                str(first_variable),
                str(second_variable),
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "The numeric association could not be completed. "
                "No correlation result has been reported."
            )
        else:
            st.session_state[result_key] = {
                "first_variable": first_variable,
                "second_variable": second_variable,
                "result": association,
            }

    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Select two numeric variables, then analyse their relationship.")
        return
    if (
        saved["first_variable"] != first_variable
        or saved["second_variable"] != second_variable
    ):
        st.info("Run the analysis again to apply the changed variable selection.")
        return

    result = saved["result"]
    metadata = result.metadata
    st.markdown("#### Correlation results")
    metrics = st.columns(4)
    metrics[0].metric("Complete pairs", f"{metadata['valid_n']:,}")
    metrics[1].metric("Excluded records", f"{metadata['excluded_n']:,}")
    metrics[2].metric("Pearson's r", f"{metadata['pearson_r']:.4f}")
    metrics[3].metric("Spearman's rho", f"{metadata['spearman_rho']:.4f}")

    pcols = st.columns(2)
    pcols[0].metric("Pearson p-value", f"{metadata['pearson_p_value']:.4g}")
    pcols[1].metric("Spearman p-value", f"{metadata['spearman_p_value']:.4g}")
    ci = metadata.get("pearson_confidence_interval_95")
    if ci is not None:
        st.caption(
            f"Pearson's r 95% confidence interval: [{ci[0]:.4f}, {ci[1]:.4f}]."
        )

    st.markdown("#### Scatterplot")
    chart_data = result.tables["paired_observations"]
    st.scatter_chart(
        chart_data,
        x=first_variable,
        y=second_variable,
        use_container_width=True,
    )
    st.caption(
        "Inspect the point pattern for curvature, outliers, clusters and "
        "restricted ranges. Correlation coefficients alone do not reveal these features."
    )

    st.markdown("#### Descriptive summary")
    st.dataframe(result.tables["descriptive_summary"], use_container_width=True)
    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    st.info(
        "Pearson's r summarises linear association. Spearman's rho summarises "
        "monotonic association based on ranks. A low p-value is not proof of "
        "a strong or important relationship, and neither coefficient implies causation."
    )
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)



def render_regression_diagnostics(fitted_data, predictor_variables, outcome_variable):
    """Display shared OLS diagnostics alongside either regression workflow."""
    st.markdown("#### Model diagnostics")
    try:
        diagnostics = run_regression_diagnostics_service(
            fitted_data, list(predictor_variables), str(outcome_variable)
        )
    except (TypeError, ValueError) as exc:
        st.warning(f"Diagnostics could not be completed: {exc}")
        return
    except Exception:
        st.warning("Diagnostics could not be completed for this fitted model.")
        return
    st.dataframe(diagnostics.tables["diagnostics"], hide_index=True, use_container_width=True)
    plot_data = diagnostics.tables["residual_plot_data"]
    st.caption("Residuals should generally be scattered around zero without a clear curve, funnel shape or systematic pattern.")
    st.scatter_chart(plot_data[["Fitted outcome", "Residual"]], x="Fitted outcome", y="Residual", use_container_width=True)
    st.markdown("##### Records for influence review")
    st.dataframe(diagnostics.tables["influential_observations"], hide_index=True, use_container_width=True)
    with st.expander("Diagnostic interpretation and cautions"):
        for finding in diagnostics.findings:
            st.write(f"• {finding}")
        for warning in diagnostics.limitations:
            st.warning(warning)


def render_simple_linear_regression(df):
    """Render guided one-predictor linear regression."""
    st.subheader("Estimate an outcome using one numeric predictor")
    st.write(
        "Simple linear regression estimates how a numeric outcome changes "
        "with one numeric predictor. For example, it can estimate the average "
        "change in assessment score associated with an additional training hour, "
        "or the change in expenditure associated with household income."
    )
    numeric_candidates = [
        column for column in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[column].dtype)
    ]
    if len(numeric_candidates) < 2:
        st.info(
            "Regression requires at least two numeric variables: one predictor "
            "and one outcome."
        )
        return

    left, right = st.columns(2)
    predictor_variable = left.selectbox(
        "Predictor variable (X)",
        numeric_candidates,
        key="simple_regression_predictor",
        help="The variable used to estimate or explain variation in the outcome.",
    )
    outcome_options = [item for item in numeric_candidates if item != predictor_variable]
    outcome_variable = right.selectbox(
        "Outcome variable (Y)",
        outcome_options,
        key="simple_regression_outcome",
        help="The numeric variable the model will estimate.",
    )
    st.caption(
        "The direction matters: predicting Y from X is not the same model as "
        "predicting X from Y. At least three complete finite records are required."
    )

    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_simple_regression_{dataset_key}"
    if st.button(
        "Run linear regression",
        type="primary",
        key="run_simple_linear_regression",
    ):
        try:
            regression = run_simple_linear_regression_service(
                df,
                str(predictor_variable),
                str(outcome_variable),
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "The regression model could not be estimated. "
                "No model results have been reported."
            )
        else:
            st.session_state[result_key] = {
                "predictor_variable": predictor_variable,
                "outcome_variable": outcome_variable,
                "result": regression,
            }

    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Choose X and Y, then run the regression model.")
        return
    if (
        saved["predictor_variable"] != predictor_variable
        or saved["outcome_variable"] != outcome_variable
    ):
        st.info("Run the model again to apply the changed variable selection.")
        return

    result = saved["result"]
    metadata = result.metadata
    st.markdown("#### Model results")
    metrics = st.columns(4)
    metrics[0].metric("Complete records", f"{metadata['valid_n']:,}")
    metrics[1].metric("R²", f"{metadata['r_squared']:.4f}")
    metrics[2].metric("Adjusted R²", f"{metadata['adjusted_r_squared']:.4f}")
    metrics[3].metric("RMSE", f"{metadata['rmse']:.4g}")

    slope_ci = metadata["slope_confidence_interval_95"]
    st.markdown("#### Estimated coefficients")
    st.dataframe(result.tables["coefficients"], use_container_width=True)
    st.caption(
        f"Estimated equation: {outcome_variable} = "
        f"{metadata['intercept']:.4g} + "
        f"({metadata['slope']:.4g} × {predictor_variable}). "
        f"Slope p-value: {metadata['slope_p_value']:.4g}; "
        f"slope 95% confidence interval: [{slope_ci[0]:.4g}, {slope_ci[1]:.4g}]."
    )

    st.markdown("#### Observed values and fitted line")
    fitted = result.tables["fitted_data"]
    observed = fitted[[predictor_variable, outcome_variable]]
    st.scatter_chart(
        observed,
        x=predictor_variable,
        y=outcome_variable,
        use_container_width=True,
    )
    fitted_line = fitted[[predictor_variable, "Fitted outcome"]].drop_duplicates(
        subset=[predictor_variable]
    ).set_index(predictor_variable)
    st.line_chart(fitted_line, use_container_width=True)
    st.caption(
        "The scatterplot shows observed records. The fitted line shows model "
        "estimates over the observed predictor range."
    )

    st.markdown("#### Residual review")
    residuals = fitted[[predictor_variable, "Residual"]].copy()
    st.scatter_chart(
        residuals,
        x=predictor_variable,
        y="Residual",
        use_container_width=True,
    )
    st.caption(
        "Residuals are observed minus fitted outcomes. Look for curvature, "
        "changing spread, clusters and unusually large residuals."
    )
    render_regression_diagnostics(fitted, [predictor_variable], outcome_variable)

    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    st.info(
        "R² describes the proportion of observed outcome variation explained "
        "by this fitted model; it does not show causation or prove that the "
        "model is appropriate. A statistically significant slope is not "
        "necessarily practically important."
    )
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)



def render_multiple_linear_regression(df):
    """Render guided regression with multiple numeric predictors."""
    st.subheader("Estimate an outcome using several numeric predictors")
    st.write(
        "Multiple linear regression estimates the association between a "
        "numeric outcome and two or more predictors at the same time. Each "
        "coefficient describes the association with the outcome while holding "
        "the other selected predictors constant."
    )
    numeric_candidates = [
        column for column in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[column].dtype)
    ]
    if len(numeric_candidates) < 3:
        st.info(
            "This analysis requires at least three numeric variables: "
            "one outcome and at least two predictors."
        )
        return

    outcome_variable = st.selectbox(
        "Outcome variable (Y)",
        numeric_candidates,
        key="multiple_regression_outcome",
        help="The numeric variable the model will estimate.",
    )
    predictor_options = [
        item for item in numeric_candidates if item != outcome_variable
    ]
    predictor_variables = st.multiselect(
        "Predictor variables (X)",
        predictor_options,
        key="multiple_regression_predictors",
        help="Select at least two variables that may help explain variation in the outcome.",
        max_selections=20,
    )
    st.caption(
        "TimanStat checks for insufficient records and perfectly or near-perfectly "
        "collinear predictors. Select predictors based on the research question, "
        "not only on statistical significance."
    )
    if len(predictor_variables) < 2:
        st.info("Select at least two predictors to run multiple regression.")
        return

    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_multiple_regression_{dataset_key}"
    if st.button(
        "Run multiple regression",
        type="primary",
        key="run_multiple_linear_regression",
    ):
        try:
            regression = run_multiple_linear_regression_service(
                df,
                list(predictor_variables),
                str(outcome_variable),
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "The multiple regression model could not be estimated. "
                "No model results have been reported."
            )
        else:
            st.session_state[result_key] = {
                "predictors": list(predictor_variables),
                "outcome": outcome_variable,
                "result": regression,
            }

    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Choose the outcome and at least two predictors, then run the model.")
        return
    if (
        saved["predictors"] != list(predictor_variables)
        or saved["outcome"] != outcome_variable
    ):
        st.info("Run the model again to apply the changed variable selection.")
        return

    result = saved["result"]
    metadata = result.metadata
    st.markdown("#### Model results")
    metrics = st.columns(4)
    metrics[0].metric("Complete records", f"{metadata['valid_n']:,}")
    metrics[1].metric("R²", f"{metadata['r_squared']:.4f}")
    metrics[2].metric("Adjusted R²", f"{metadata['adjusted_r_squared']:.4f}")
    metrics[3].metric("RMSE", f"{metadata['rmse']:.4g}")
    st.caption(
        f"Overall model F-statistic: {metadata['model_f_statistic']:.4g}; "
        f"p-value: {metadata['model_p_value']:.4g}. "
        "The overall test evaluates whether the included predictors jointly "
        "improve on an intercept-only model."
    )

    st.markdown("#### Adjusted coefficient estimates")
    st.dataframe(result.tables["coefficients"], use_container_width=True)
    st.caption(
        "Each predictor coefficient is adjusted for the other predictors in "
        "this model. Interpret units and confidence intervals in the context "
        "of the variables and study design."
    )

    fitted = result.tables["fitted_data"]
    st.markdown("#### Observed versus fitted outcomes")
    st.scatter_chart(
        fitted[[outcome_variable, "Fitted outcome"]],
        x="Fitted outcome",
        y=outcome_variable,
        use_container_width=True,
    )
    st.markdown("#### Residual review")
    st.scatter_chart(
        fitted[["Fitted outcome", "Residual"]],
        x="Fitted outcome",
        y="Residual",
        use_container_width=True,
    )
    render_regression_diagnostics(fitted, list(predictor_variables), outcome_variable)
    st.caption(
        "Residuals are observed minus fitted outcomes. Look for systematic "
        "patterns, changing spread, clusters and unusually large residuals."
    )

    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    st.info(
        "Adjusted coefficients are conditional associations, not causal "
        "effects. R² is not proof of model validity, and a small p-value does "
        "not establish practical importance. Predictor selection should be "
        "guided by subject knowledge and the study objective."
    )
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)




def render_categorical_model_recommender(df):
    """Guide users to the correct regression family for categorical outcomes."""
    st.subheader("Choose the appropriate categorical-outcome model")
    st.write(
        "TimanStat first checks how many outcome categories are observed. "
        "For three or more categories, you must confirm whether the categories "
        "have a meaningful order. Category labels and storage order are never "
        "used to guess this."
    )
    candidates = [
        column for column in df.columns
        if 2 <= df[column].dropna().nunique()
    ]
    if not candidates:
        st.info("No outcome with at least two observed categories was detected.")
        return
    outcome = st.selectbox(
        "Select the outcome you want to explain",
        candidates,
        key="categorical_model_recommender_outcome",
    )
    category_count = int(df[outcome].dropna().nunique())
    structure = None
    if category_count >= 3:
        structure = st.selectbox(
            "Do these categories have a meaningful order?",
            options=["ordered", "nominal"],
            index=None,
            placeholder="Select ordered or unordered",
            format_func=lambda value: (
                "Yes — ordered levels (e.g. low, moderate, high)"
                if value == "ordered"
                else "No — unordered categories (e.g. assistance type)"
            ),
            key="categorical_model_recommender_structure",
        )
    try:
        recommendation = recommend_categorical_outcome_model_service(
            df, outcome, structure
        )
    except (TypeError, ValueError) as exc:
        st.error(str(exc))
        return
    metadata = recommendation.metadata
    st.caption(
        f"{metadata['valid_n']:,} non-missing outcome records; "
        f"{metadata['category_count']} observed categories."
    )
    st.markdown("**Observed category frequencies**")
    st.dataframe(
        pd.DataFrame(
            [{"Category": category, "Frequency": count}
             for category, count in metadata["category_counts"].items()]
        ),
        hide_index=True,
        use_container_width=True,
    )
    if metadata["status"] == "not_suitable":
        st.warning("This outcome is not currently suitable for categorical regression.")
    elif metadata["status"] == "needs_classification":
        st.info(
            "Confirm whether the outcome is ordered or nominal to receive a model recommendation."
        )
    else:
        labels = {
            "binary_logistic": "Binary logistic regression",
            "ordinal_logistic": "Ordinal logistic regression",
            "multinomial_logistic": "Multinomial logistic regression",
        }
        st.success(f"Recommended starting point: {labels[metadata['recommended_model']]}")
    for finding in recommendation.findings:
        st.write(f"- {finding}")
    for warning in recommendation.limitations:
        st.warning(warning)
    st.caption(
        "This is a model-family recommendation, not an automatic fit. "
        "Predictor suitability, sample size, assumptions and study design "
        "must still be checked before estimation."
    )


def render_binary_logistic_regression(df):
    """Render guided binary logistic regression for a two-category outcome."""
    st.subheader("Estimate the probability of a binary outcome")
    st.write(
        "Binary logistic regression estimates the probability of an event, "
        "such as completing training, accessing a service or remaining in "
        "business. Choose the event category explicitly so odds ratios and "
        "predicted probabilities have an unambiguous interpretation."
    )
    numeric_predictors = [
        column for column in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[column].dtype)
    ]
    binary_outcomes = [
        column for column in df.columns
        if df[column].dropna().nunique() == 2
    ]
    if not binary_outcomes:
        st.info("No variable with exactly two observed outcome categories was detected.")
        return
    if not numeric_predictors:
        st.info("At least one numeric predictor is required in this guided version.")
        return

    outcome_variable = st.selectbox(
        "Binary outcome variable",
        binary_outcomes,
        key="binary_logistic_outcome",
    )
    categories = list(pd.unique(df[outcome_variable].dropna()))
    positive_default = next(
        (i for i, value in enumerate(categories) if value == 1 or value is True),
        1,
    )
    positive_class = st.selectbox(
        "Which category represents the event (positive outcome)?",
        categories,
        index=positive_default,
        key="binary_logistic_positive_class",
        format_func=lambda value: str(value),
        help="Odds ratios above 1 indicate higher odds of this selected event.",
    )
    predictor_options = [
        column for column in numeric_predictors if column != outcome_variable
    ]
    if not predictor_options:
        st.info("Choose an outcome that leaves at least one numeric predictor available.")
        return
    predictors = st.multiselect(
        "Numeric predictor variables",
        predictor_options,
        key="binary_logistic_predictors",
        help="Select variables that may be associated with the event.",
        max_selections=20,
    )
    st.caption(
        "Categorical predictors and survey-design adjustments are not yet "
        "included in this guided version. Do not encode categories as arbitrary "
        "numbers and treat them as continuous predictors."
    )
    if not predictors:
        st.info("Select at least one numeric predictor to run logistic regression.")
        return

    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_binary_logistic_{dataset_key}"
    if st.button("Run binary logistic regression", type="primary", key="run_binary_logistic"):
        try:
            model = run_binary_logistic_regression_service(
                df, list(predictors), str(outcome_variable), positive_class
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "The logistic regression model could not be estimated. "
                "No model results have been reported."
            )
        else:
            st.session_state[result_key] = {
                "predictors": list(predictors),
                "outcome": outcome_variable,
                "positive_class": positive_class,
                "result": model,
            }

    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Choose the outcome, event category and predictors, then run the model.")
        return
    if (
        saved["predictors"] != list(predictors)
        or saved["outcome"] != outcome_variable
        or saved["positive_class"] != positive_class
    ):
        st.info("Run the model again to apply the changed variable selection.")
        return

    result = saved["result"]
    metadata = result.metadata
    st.markdown("#### Model results")
    metrics = st.columns(4)
    metrics[0].metric("Complete records", f"{metadata['valid_n']:,}")
    metrics[1].metric("Events", f"{metadata['event_n']:,}")
    metrics[2].metric("McFadden pseudo-R²", f"{metadata['mcfadden_pseudo_r_squared']:.4f}")
    metrics[3].metric("Brier score", f"{metadata['brier_score']:.4f}")
    st.caption(
        f"Event: {metadata['positive_class']}; non-event: "
        f"{metadata['negative_class']}. Overall likelihood-ratio "
        f"chi-square({metadata['predictor_count']}) = "
        f"{metadata['likelihood_ratio_chi_square']:.4g}; "
        f"p-value = {metadata['model_p_value']:.4g}; AIC = {metadata['aic']:.4g}."
    )
    st.markdown("#### Adjusted odds ratios")
    st.dataframe(result.tables["coefficients"], hide_index=True, use_container_width=True)
    st.caption(
        "An odds ratio above 1 indicates higher odds of the selected event "
        "per one-unit increase in a predictor; below 1 indicates lower odds. "
        "Interpret each estimate while holding the other included predictors constant."
    )
    fitted = result.tables["fitted_data"]
    st.markdown("#### Observed outcomes and predicted probabilities")
    st.scatter_chart(
        fitted[["Predicted probability", "Observed event"]],
        x="Predicted probability",
        y="Observed event",
        use_container_width=True,
    )
    st.dataframe(
        fitted[[outcome_variable, "Predicted probability", "Predicted class (0.5 threshold)"]].head(100),
        hide_index=True,
        use_container_width=True,
    )
    st.caption("The table shows up to the first 100 complete records. Classification uses a 0.5 threshold for illustration, not as a universal decision threshold.")
    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    st.info(
        "Predicted probabilities describe model-based estimates, not guarantees. "
        "Odds ratios are adjusted associations, not causal effects. Assess "
        "calibration and predictive performance on data not used to fit the model."
    )
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)





def render_multinomial_logistic_regression(df):
    """Render guided multinomial logistic regression for nominal outcomes."""
    st.subheader("Analyse an unordered categorical outcome")
    st.write(
        "Multinomial logistic regression is appropriate when an outcome has "
        "three or more mutually exclusive categories without a meaningful "
        "ranking, such as assistance type, referral destination or preferred "
        "service channel."
    )
    candidates = [
        column for column in df.columns
        if df[column].dropna().nunique() >= 3
    ]
    numeric_predictors = [
        column for column in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[column].dtype)
    ]
    if not candidates or not numeric_predictors:
        st.info("A nominal outcome with at least three categories and one numeric predictor is required.")
        return
    outcome = st.selectbox(
        "Nominal outcome variable", candidates, key="multinomial_logistic_outcome"
    )
    categories = list(pd.unique(df[outcome].dropna()))
    if len(categories) < 3:
        st.info("Select an outcome with at least three observed categories.")
        return
    reference = st.selectbox(
        "Reference category", categories, index=len(categories) - 1,
        key="multinomial_logistic_reference", format_func=str,
        help="Every other category will be compared with this reference category.",
    )
    predictor_options = [c for c in numeric_predictors if c != outcome]
    if not predictor_options:
        st.info("Choose an outcome that leaves at least one numeric predictor available.")
        return
    predictors = st.multiselect(
        "Numeric predictor variables", predictor_options,
        key="multinomial_logistic_predictors", max_selections=15,
    )
    st.caption(
        "Confirm that categories are genuinely unordered. If they have a "
        "meaningful progression, use ordinal logistic regression instead. "
        "Categorical predictors and complex survey adjustments are not yet included."
    )
    if not predictors:
        st.info("Select at least one numeric predictor to run the model.")
        return
    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_multinomial_logistic_{dataset_key}"
    if st.button("Run multinomial logistic regression", type="primary", key="run_multinomial_logistic"):
        try:
            model = run_multinomial_logistic_regression_service(
                df, list(predictors), str(outcome), reference
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("The multinomial model could not be estimated. No inferential result has been reported.")
        else:
            st.session_state[result_key] = {
                "predictors": list(predictors), "outcome": outcome,
                "reference": reference, "result": model,
            }
    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Confirm the nominal outcome and reference category, select predictors, then run the model.")
        return
    if (saved["predictors"] != list(predictors)
        or saved["outcome"] != outcome or saved["reference"] != reference):
        st.info("Run the model again to apply the changed variable selection.")
        return
    result = saved["result"]
    metadata = result.metadata
    metrics = st.columns(3)
    metrics[0].metric("Complete records", f"{metadata['valid_n']:,}")
    metrics[1].metric("Outcome categories", metadata["category_count"])
    metrics[2].metric("AIC", f"{metadata['aic']:.3f}")
    st.caption(
        f"Reference category: {metadata['reference_category']}; "
        f"overall likelihood-ratio chi-square({metadata['likelihood_ratio_df']}) = "
        f"{metadata['likelihood_ratio_chi_square']:.4g}; p = {metadata['model_p_value']:.4g}."
    )
    st.markdown("#### Category-versus-reference effects")
    st.dataframe(result.tables["coefficients"], hide_index=True, use_container_width=True)
    st.caption(
        "Relative risk ratios above 1 indicate higher relative odds of the "
        "listed category rather than the reference category, holding other "
        "predictors constant."
    )
    st.markdown("#### Predicted category probabilities")
    st.dataframe(result.tables["category_probabilities"].head(100), hide_index=True, use_container_width=True)
    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"- {finding}")
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)


def render_ordinal_logistic_regression(df):
    """Render guided proportional-odds ordinal logistic regression."""
    st.subheader("Analyse an ordered categorical outcome")
    st.write(
        "Ordinal logistic regression is suitable when an outcome has three or "
        "more categories with a meaningful order, such as food security levels, "
        "satisfaction ratings or training performance bands."
    )
    candidates = [
        column for column in df.columns
        if 3 <= df[column].dropna().nunique() <= 8
    ]
    numeric_predictors = [
        column for column in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[column].dtype)
    ]
    if not candidates:
        st.info("No outcome with 3–8 observed categories was detected.")
        return
    outcome = st.selectbox(
        "Ordered outcome variable", candidates, key="ordinal_logistic_outcome"
    )
    categories = list(pd.unique(df[outcome].dropna()))
    st.markdown("**Specify the category order from lowest to highest.**")
    st.caption(
        "TimanStat will not guess whether categories such as 1, 2, 3 or "
        "Poor, Fair, Good are ordered. Confirm the correct substantive order."
    )
    ordered = []
    for position in range(len(categories)):
        available = [value for value in categories if value not in ordered]
        selected = st.selectbox(
            f"Category {position + 1} (rank {position + 1})",
            available,
            key=f"ordinal_logistic_order_{_dataset_analysis_key(df)[:10]}_{position}_{repr(tuple(ordered))}",
            format_func=str,
        )
        ordered.append(selected)
    predictor_options = [
        column for column in numeric_predictors if column != outcome
    ]
    if not predictor_options:
        st.info("At least one numeric predictor is required in this guided version.")
        return
    predictors = st.multiselect(
        "Numeric predictor variables",
        predictor_options,
        key="ordinal_logistic_predictors",
        max_selections=15,
        help="Select numeric variables that may be associated with movement towards higher outcome categories.",
    )
    st.caption(
        "This guided version does not yet include categorical predictors or "
        "complex survey-design adjustments. Avoid treating arbitrary category "
        "codes as continuous predictors."
    )
    if not predictors:
        st.info("Select at least one numeric predictor to continue.")
        return
    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_ordinal_logistic_{dataset_key}"
    if st.button(
        "Run ordinal logistic regression",
        type="primary",
        key="run_ordinal_logistic",
    ):
        try:
            model = run_ordinal_logistic_regression_service(
                df, list(predictors), str(outcome), ordered
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error(
                "The ordinal model could not be estimated. No inferential "
                "result has been reported."
            )
        else:
            st.session_state[result_key] = {
                "predictors": list(predictors),
                "outcome": outcome,
                "ordered_categories": ordered,
                "result": model,
            }
    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Confirm the category order, select predictors and run the model.")
        return
    if (
        saved["predictors"] != list(predictors)
        or saved["outcome"] != outcome
        or saved["ordered_categories"] != ordered
    ):
        st.info("Run the model again to apply the changed category order or predictors.")
        return
    result = saved["result"]
    metadata = result.metadata
    st.markdown("#### Model results")
    metrics = st.columns(3)
    metrics[0].metric("Complete records", f"{metadata['valid_n']:,}")
    metrics[1].metric("Outcome categories", len(ordered))
    metrics[2].metric("AIC", f"{metadata['aic']:.3f}")
    st.caption(
        f"Overall likelihood-ratio chi-square({metadata['predictor_count']}) = "
        f"{metadata['likelihood_ratio_chi_square']:.4g}; "
        f"p-value = {metadata['model_p_value']:.4g}."
    )
    st.markdown("#### Adjusted common odds ratios")
    st.dataframe(result.tables["coefficients"], hide_index=True, use_container_width=True)
    st.caption(
        "An odds ratio above 1 indicates greater odds of being in a higher "
        "rather than lower outcome category, under the proportional-odds model."
    )
    st.markdown("#### Predicted category probabilities")
    st.dataframe(
        result.tables["category_probabilities"].head(100),
        hide_index=True,
        use_container_width=True,
    )
    st.caption("Predicted probabilities are shown for up to the first 100 complete records.")
    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)



def render_poisson_regression(df):
    """Render guided Poisson regression for count outcomes."""
    st.subheader("Model a count outcome")
    st.write(
        "Poisson regression models the expected number or rate of events, "
        "such as household visits, referrals, incidents or service contacts."
    )
    numeric_columns = [
        column for column in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[column].dtype)
    ]
    candidates = []
    for column in numeric_columns:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if not values.empty and (values >= 0).all() and np.allclose(
            values.to_numpy(dtype=float),
            np.round(values.to_numpy(dtype=float)),
            atol=1e-10,
        ):
            candidates.append(column)
    if not candidates:
        st.info("No numeric variable with non-negative integer values was detected as a possible count outcome.")
        return
    outcome = st.selectbox(
        "Count outcome variable", candidates, key="poisson_outcome"
    )
    exposure_options = [None] + [c for c in numeric_columns if c != outcome]
    exposure = st.selectbox(
        "Exposure variable (optional)",
        exposure_options,
        index=0,
        format_func=lambda value: "No exposure offset" if value is None else str(value),
        key="poisson_exposure",
        help="Use a positive exposure measure such as person-time, population at risk or observation duration. Its log is included as an offset.",
    )
    predictor_options = [
        c for c in numeric_columns if c != outcome and c != exposure
    ]
    if not predictor_options:
        st.info("At least one numeric predictor is required in this guided version.")
        return
    predictors = st.multiselect(
        "Numeric predictor variables",
        predictor_options,
        key="poisson_predictors",
        max_selections=15,
        help="Select numeric variables associated with the expected count or event rate.",
    )
    st.caption(
        "The current guided version supports numeric predictors only. "
        "Categorical predictors, clustered observations and complex survey "
        "design adjustments are not yet included."
    )
    if not predictors:
        st.info("Select at least one predictor to continue.")
        return
    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_poisson_{dataset_key}"
    if st.button("Run Poisson regression", type="primary", key="run_poisson_regression"):
        try:
            model = run_poisson_regression_service(
                df, list(predictors), str(outcome), exposure
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("The Poisson model could not be estimated. No inferential result has been reported.")
        else:
            st.session_state[result_key] = {
                "predictors": list(predictors),
                "outcome": outcome,
                "exposure": exposure,
                "result": model,
            }
    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Select the count outcome and predictors, then run the model.")
        return
    if (
        saved["predictors"] != list(predictors)
        or saved["outcome"] != outcome
        or saved["exposure"] != exposure
    ):
        st.info("Run the model again to apply the changed variable selection.")
        return
    result = saved["result"]
    metadata = result.metadata
    metrics = st.columns(4)
    metrics[0].metric("Complete records", f"{metadata['valid_n']:,}")
    metrics[1].metric("AIC", f"{metadata['aic']:.2f}")
    metrics[2].metric("Dispersion", f"{metadata['dispersion']:.2f}")
    metrics[3].metric("Model p-value", f"{metadata['model_p_value']:.4g}")
    st.markdown("#### Incidence rate ratios")
    st.dataframe(result.tables["coefficients"], hide_index=True, use_container_width=True)
    st.caption(
        "An IRR above 1 indicates a higher expected event rate per unit increase "
        "in the predictor; an IRR below 1 indicates a lower expected rate. "
        "Interpret estimates in the units of the selected predictor."
    )
    st.markdown("#### Observed and predicted counts")
    st.dataframe(result.tables["fitted_data"].head(100), use_container_width=True)
    st.caption("The fitted-count table shows up to the first 100 complete records.")
    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)



def render_negative_binomial_regression(df):
    """Render guided NB2 regression for overdispersed count outcomes."""
    st.subheader("Model an overdispersed count outcome")
    st.write(
        "Negative binomial regression is a count-data model that allows the "
        "conditional variance to exceed the conditional mean. It is often "
        "considered when Poisson diagnostics indicate overdispersion."
    )
    numeric_columns = [
        column for column in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[column].dtype)
    ]
    candidates = []
    for column in numeric_columns:
        values = pd.to_numeric(df[column], errors="coerce").dropna()
        if not values.empty and (values >= 0).all() and np.allclose(
            values.to_numpy(dtype=float), np.round(values.to_numpy(dtype=float)), atol=1e-10
        ):
            candidates.append(column)
    if not candidates:
        st.info("No numeric variable with non-negative integer values was detected as a possible count outcome.")
        return
    outcome = st.selectbox("Count outcome variable", candidates, key="negative_binomial_outcome")
    exposure_options = [None] + [c for c in numeric_columns if c != outcome]
    exposure = st.selectbox(
        "Exposure variable (optional)", exposure_options, index=0,
        format_func=lambda value: "No exposure offset" if value is None else str(value),
        key="negative_binomial_exposure",
        help="Use a positive exposure measure such as person-time, population at risk or observation duration.",
    )
    predictor_options = [c for c in numeric_columns if c != outcome and c != exposure]
    if not predictor_options:
        st.info("At least one numeric predictor is required in this guided version.")
        return
    predictors = st.multiselect(
        "Numeric predictor variables", predictor_options,
        key="negative_binomial_predictors", max_selections=15,
    )
    st.caption(
        "This guided version supports numeric predictors only. It does not "
        "adjust for complex survey designs, clustered observations or repeated measures."
    )
    if not predictors:
        st.info("Select at least one predictor to continue.")
        return
    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_negative_binomial_{dataset_key}"
    if st.button("Run negative binomial regression", type="primary", key="run_negative_binomial_regression"):
        try:
            model = run_negative_binomial_regression_service(
                df, list(predictors), str(outcome), exposure
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("The negative binomial model could not be estimated. No inferential result has been reported.")
        else:
            st.session_state[result_key] = {
                "predictors": list(predictors), "outcome": outcome,
                "exposure": exposure, "result": model,
            }
    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Select the count outcome and predictors, then run the model.")
        return
    if (saved["predictors"] != list(predictors)
        or saved["outcome"] != outcome or saved["exposure"] != exposure):
        st.info("Run the model again to apply the changed variable selection.")
        return
    result = saved["result"]
    metadata = result.metadata
    metrics = st.columns(4)
    metrics[0].metric("Complete records", f"{metadata['valid_n']:,}")
    metrics[1].metric("NB2 alpha", f"{metadata['dispersion_alpha']:.4g}")
    metrics[2].metric("NB2 AIC", f"{metadata['aic']:.2f}")
    metrics[3].metric("Poisson AIC", f"{metadata['poisson_aic']:.2f}")
    st.caption(
        f"Likelihood-ratio chi-square({metadata['predictor_count']}) = "
        f"{metadata['likelihood_ratio_chi_square']:.4g}; "
        f"p-value = {metadata['model_p_value']:.4g}. "
        "The AIC comparison uses the same complete records; lower AIC indicates "
        "better relative fit among the compared models."
    )
    st.markdown("#### Incidence rate ratios")
    st.dataframe(result.tables["coefficients"], hide_index=True, use_container_width=True)
    st.caption(
        "IRRs describe multiplicative changes in the expected count rate per "
        "unit increase in a predictor, holding other predictors constant."
    )
    st.markdown("#### Observed and predicted counts")
    st.dataframe(result.tables["fitted_data"].head(100), use_container_width=True)
    st.caption("The fitted-count table shows up to the first 100 complete records.")
    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)



def _survival_variable_options(df):
    time_options = [
        c for c in df.select_dtypes(include="number").columns
        if not pd.api.types.is_bool_dtype(df[c].dtype)
    ]
    event_options = [
        c for c in df.columns if 2 <= df[c].dropna().nunique() == 2
    ]
    return time_options, event_options


def render_kaplan_meier_analysis(df):
    """Render Kaplan-Meier survival curves and optional log-rank test."""
    st.subheader("Estimate time-to-event outcomes")
    st.write(
        "Kaplan-Meier analysis estimates the probability of remaining event-free "
        "over time while accounting for right-censored observations, such as "
        "participants who have not yet obtained employment by the end of follow-up."
    )
    time_options, event_options = _survival_variable_options(df)
    if not time_options or not event_options:
        st.info("A numeric follow-up-time variable and a two-category event-status variable are required.")
        return
    time_variable = st.selectbox("Follow-up time variable", time_options, key="km_time")
    event_variable = st.selectbox("Event-status variable", event_options, key="km_event")
    event_categories = list(pd.unique(df[event_variable].dropna()))
    event_value = st.selectbox(
        "Which category represents the event of interest?",
        event_categories, key="km_event_value", format_func=str,
        help="For example, select 'employed' as the event; 'censored' records represent participants without the event by last follow-up.",
    )
    group_options = [None] + [c for c in df.columns if c not in {time_variable, event_variable}]
    group_variable = st.selectbox(
        "Compare groups (optional)", group_options, index=0,
        format_func=lambda value: "No grouping" if value is None else str(value),
        key="km_group",
    )
    st.caption(
        "The log-rank test is provided when exactly two groups are selected. "
        "With more groups, TimanStat displays separate curves without an overall test."
    )
    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_kaplan_meier_{dataset_key}"
    if st.button("Run Kaplan-Meier analysis", type="primary", key="run_kaplan_meier"):
        try:
            result = run_kaplan_meier_service(
                df, str(time_variable), str(event_variable), event_value, group_variable
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("The Kaplan-Meier analysis could not be estimated.")
        else:
            st.session_state[result_key] = {
                "time": time_variable, "event": event_variable,
                "event_value": event_value, "group": group_variable,
                "result": result,
            }
    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Select follow-up time, event status and the event category, then run the analysis.")
        return
    if (saved["time"] != time_variable or saved["event"] != event_variable
        or saved["event_value"] != event_value or saved["group"] != group_variable):
        st.info("Run the analysis again to apply the changed variable selections.")
        return
    result = saved["result"]
    metadata = result.metadata
    metrics = st.columns(4)
    metrics[0].metric("Records analysed", f"{metadata['valid_n']:,}")
    metrics[1].metric("Events", f"{metadata['event_n']:,}")
    metrics[2].metric("Censored", f"{metadata['censored_n']:,}")
    median = metadata["median_survival_time"]
    metrics[3].metric("Median survival", "Not reached" if median is None else f"{median:.3g}")
    st.markdown("#### Survival curve")
    if "group_survival_curves" in result.tables:
        grouped = result.tables["group_survival_curves"]
        for label, subset in grouped.groupby("Group", sort=False):
            st.markdown(f"**{label}**")
            st.line_chart(
                subset.set_index("Time")[["Survival probability"]],
                y="Survival probability", use_container_width=True,
            )
        st.dataframe(grouped, hide_index=True, use_container_width=True)
    else:
        curve = result.tables["survival_curve"]
        if not curve.empty:
            st.line_chart(
                curve.set_index("Time")[["Survival probability"]],
                y="Survival probability", use_container_width=True,
            )
        st.dataframe(curve, hide_index=True, use_container_width=True)
    if metadata.get("logrank_test"):
        test = metadata["logrank_test"]
        st.caption(
            f"Log-rank test: chi-square(1) = {test['chi_square']:.4g}; "
            f"p-value = {test['p_value']:.4g}."
        )
    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)


def render_cox_survival_regression(df):
    """Render Cox proportional hazards regression."""
    st.subheader("Identify factors associated with time to an event")
    st.write(
        "Cox regression estimates how predictors are associated with the "
        "instantaneous event hazard. It is useful for examining factors "
        "associated with earlier or later outcomes while accounting for censoring."
    )
    time_options, event_options = _survival_variable_options(df)
    if not time_options or not event_options:
        st.info("A numeric follow-up-time variable and a two-category event-status variable are required.")
        return
    time_variable = st.selectbox("Follow-up time variable", time_options, key="cox_time")
    event_variable = st.selectbox("Event-status variable", event_options, key="cox_event")
    event_categories = list(pd.unique(df[event_variable].dropna()))
    event_value = st.selectbox(
        "Which category represents the event of interest?",
        event_categories, key="cox_event_value", format_func=str,
    )
    predictor_options = [
        c for c in df.select_dtypes(include="number").columns
        if c not in {time_variable, event_variable}
        and not pd.api.types.is_bool_dtype(df[c].dtype)
    ]
    if not predictor_options:
        st.info("At least one numeric predictor is required.")
        return
    predictors = st.multiselect(
        "Numeric predictors", predictor_options,
        key="cox_predictors", max_selections=15,
    )
    st.caption(
        "The current guided model uses Breslow handling for tied event times. "
        "The proportional hazards assumption is not yet formally tested. "
        "Categorical predictors and complex survey adjustments are not supported."
    )
    if not predictors:
        st.info("Select at least one predictor to run Cox regression.")
        return
    dataset_key = _dataset_analysis_key(df)
    result_key = f"timanstat_cox_{dataset_key}"
    if st.button("Run Cox regression", type="primary", key="run_cox_regression"):
        try:
            model = run_cox_survival_service(
                df, list(predictors), str(time_variable), str(event_variable), event_value
            )
        except (TypeError, ValueError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("The Cox model could not be estimated. No inferential result has been reported.")
        else:
            st.session_state[result_key] = {
                "predictors": list(predictors), "time": time_variable,
                "event": event_variable, "event_value": event_value,
                "result": model,
            }
    saved = st.session_state.get(result_key)
    if not saved:
        st.info("Select the time and event variables, choose the event category and predictors, then run the model.")
        return
    if (saved["predictors"] != list(predictors) or saved["time"] != time_variable
        or saved["event"] != event_variable or saved["event_value"] != event_value):
        st.info("Run the model again to apply the changed variable selections.")
        return
    result = saved["result"]
    metadata = result.metadata
    metrics = st.columns(3)
    metrics[0].metric("Complete records", f"{metadata['valid_n']:,}")
    metrics[1].metric("Observed events", f"{metadata['event_n']:,}")
    metrics[2].metric("Model p-value", f"{metadata['model_p_value']:.4g}")
    st.markdown("#### Adjusted hazard ratios")
    st.dataframe(result.tables["coefficients"], hide_index=True, use_container_width=True)
    st.caption(
        "A hazard ratio above 1 indicates a higher instantaneous event hazard; "
        "below 1 indicates a lower hazard, holding other predictors constant."
    )
    st.markdown("#### Estimated baseline survival")
    st.line_chart(
        result.tables["baseline_survival"].set_index("Time")[["Baseline survival"]],
        y="Baseline survival", use_container_width=True,
    )
    st.markdown("#### Interpretation")
    for finding in result.findings:
        st.write(f"• {finding}")
    if result.limitations:
        st.markdown("#### Assumptions and limitations")
        for warning in result.limitations:
            st.warning(warning)


def show_under_development(page, purpose):
    """Display an honest status page for an unfinished module."""
    st.title(page)
    st.caption("Module status: 🟡 Under development")
    st.write(purpose)
    st.info(
        "This module is not yet operational. "
        "Do not use it as if it provides completed analysis."
    )


# ============================================================
# SIDEBAR: LOGO AND NAVIGATION
# ============================================================

# The corporate logo belongs to Timan Analytics, the parent company.
# It is deliberately kept separate from the TimanStat product wordmark.
corporate_logo_candidates = (
    Path(__file__).parent / "timan_analytics_logo.png",
    Path(__file__).parent / "Timan Analytics logo.jpeg",
)
corporate_logo_path = next(
    (candidate for candidate in corporate_logo_candidates if candidate.is_file()),
    None,
)

st.sidebar.markdown(
    """
    <div class="sidebar-brand">
        <div class="sidebar-symbol" aria-hidden="true">
            <span></span><span></span><span></span>
        </div>
        <div class="sidebar-wordmark">TIMAN<span>STAT</span></div>
        <div class="sidebar-platform-label">STATISTICAL SUPPORT PLATFORM</div>
        <div class="sidebar-byline">by Timan Analytics</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.divider()

# Public preview sessions do not have accounts, organisation workspaces or
# persistent subscription records. Uploaded data remains in the visitor's
# Streamlit session and is not shared with other visitors.
current_user_id = st.session_state.get("user_id") if not PUBLIC_ACCESS_MODE else None
current_role = st.session_state.get("role") if not PUBLIC_ACCESS_MODE else None

if PUBLIC_ACCESS_MODE:
    st.sidebar.info(
        "PUBLIC PREVIEW\n\n"
        "No account is required. Datasets remain in this browser session. "
        "Do not upload confidential or personally identifiable data."
    )
    st.sidebar.caption(
        "Preview limits: 25 MB per upload · 10,000 rows · "
        "100 analyses · 10 exports per browser session."
    )
else:
    try:
        user_organisations = list_user_organisations(current_user_id)
    except Exception:
        st.sidebar.error("Workspace access could not be verified.")
        st.error(
            "TimanStat could not verify your organisation access. "
            "Please refresh the page or sign in again."
        )
        st.stop()

    organisation_names = {
        item["organisation_id"]: item["organisation_name"]
        for item in user_organisations
    }
    organisation_options = [None, *organisation_names.keys()]
    if st.session_state.get("active_organisation_id") not in organisation_options:
        st.session_state.active_organisation_id = None

    st.sidebar.selectbox(
        "WORKSPACE / BILLING CONTEXT",
        options=organisation_options,
        format_func=lambda value: (
            "Personal account" if value is None else organisation_names[value]
        ),
        key="active_organisation_id",
        help=(
            "Upload limits and monthly analysis/export allowances are applied "
            "to the selected account or organisation."
        ),
    )

    try:
        active_organisation_id = st.session_state.get("active_organisation_id")
        effective_entitlements = get_effective_entitlements(
            user_id=current_user_id,
            organisation_id=active_organisation_id,
        )
        usage_owner = (
            {"organisation_id": active_organisation_id}
            if active_organisation_id
            else {"user_id": current_user_id}
        )
        analysis_used = get_monthly_usage("monthly_analyses", **usage_owner)
        export_used = get_monthly_usage("monthly_exports", **usage_owner)
        plan_limits = effective_entitlements["limits"]

        def _usage_label(used, limit):
            return f"{used:,} used · Unlimited" if limit is None else f"{used:,} / {limit:,}"

        st.sidebar.divider()
        st.sidebar.caption("SUBSCRIPTION & USAGE")
        st.sidebar.markdown(f"**{effective_entitlements['plan_name']} plan**")
        st.sidebar.caption(
            f"Monthly analyses: {_usage_label(analysis_used, plan_limits['monthly_analyses'])}"
        )
        if plan_limits["monthly_analyses"] is not None:
            st.sidebar.progress(
                min(analysis_used / plan_limits["monthly_analyses"], 1.0)
            )
        st.sidebar.caption(
            f"Monthly exports: {_usage_label(export_used, plan_limits['monthly_exports'])}"
        )
        if plan_limits["monthly_exports"] is not None:
            st.sidebar.progress(
                min(export_used / plan_limits["monthly_exports"], 1.0)
            )
    except Exception:
        st.sidebar.caption("Subscription and usage information is temporarily unavailable.")

developer_dashboard_unlocked = (
    render_developer_dashboard_access()
    if PUBLIC_ACCESS_MODE
    else current_role in {"admin", "super_admin"}
)

navigation_options = [
    name
    for name in MODULES
    if (
        (
            not PUBLIC_ACCESS_MODE
            or name not in {
                "Subscription Administration",
                "User Administration",
                "Subscription",
                "Account & Security",
            }
        )
        and (
            not PUBLIC_ACCESS_MODE
            or PUBLIC_DATABASE_AVAILABLE
            or name != "Project Status"
        )
        and (
            name != "User Administration"
            or current_role in {"admin", "super_admin"}
        )
        and (
            name != "Developer Dashboard"
            or developer_dashboard_unlocked
        )
    )
]
if st.session_state.get("navigation_page") not in navigation_options:
    st.session_state.navigation_page = "Home"

def _select_navigation_page(selected_page):
    """Set the active page from the grouped sidebar navigation."""
    st.session_state.navigation_page = selected_page


def _render_navigation_item(label):
    """Render a consistent, full-width navigation item."""
    is_active = st.session_state.get("navigation_page") == label
    st.sidebar.button(
        label,
        key=f"nav_{label.lower().replace(' ', '_').replace('&', 'and')}",
        type="primary" if is_active else "secondary",
        use_container_width=True,
        on_click=_select_navigation_page,
        args=(label,),
    )


# Navigation is organised around the user's workflow rather than a flat
# list of every module. The registry remains the single source of truth.
st.sidebar.markdown("#### WORKSPACE")
_render_navigation_item("Home")

navigation_groups = (
    (
        "DATA WORKSPACE",
        ("Data Management", "Data Quality"),
        True,
    ),
    (
        "STATISTICAL ANALYSIS",
        (
            "Descriptive Statistics",
            "Statistical Inference",
            "Survey Analysis",
            "Research & Modelling",
        ),
        True,
    ),
    (
        "INTELLIGENCE & MODELLING",
        (
            "MEAL Intelligence",
            "Business Intelligence",
            "Forecasting & Prediction",
            "Optimisation & Scenarios",
            "AI Analyst",
        ),
        False,
    ),
    (
        "VISUALISATION & OUTPUTS",
        ("Visualisations", "Reports & Exports"),
        False,
    ),
    (
        "PLATFORM",
        ("Developer Dashboard", "About"),
        False,
    ),
)

for group_label, group_pages, expanded in navigation_groups:
    available_pages = [
        name for name in group_pages if name in navigation_options
    ]
    if not available_pages:
        continue
    with st.sidebar.expander(group_label, expanded=expanded):
        for module_name in available_pages:
            _render_navigation_item(module_name)

page = st.session_state.navigation_page

if not PUBLIC_ACCESS_MODE and st.sidebar.button("Sign out", use_container_width=True):
    logout()
    oidc_user = getattr(st, "user", None)
    if oidc_user is not None and getattr(oidc_user, "is_logged_in", False):
        st.logout()
    st.rerun()

st.sidebar.divider()
st.sidebar.caption(SIDEBAR_FOOTER)

if st.session_state.dataset is not None:
    loaded = st.session_state.dataset

    st.sidebar.success(
        f"Dataset: {st.session_state.dataset_name or 'Uploaded dataset'}"
    )

    st.sidebar.caption(
        f"{loaded.shape[0]:,} rows · {loaded.shape[1]:,} columns"
    )

    st.sidebar.button(
        "Clear current dataset",
        on_click=clear_dataset,
    )
else:
    st.sidebar.caption("No dataset loaded")


# ============================================================
# HOME
# ============================================================

if page == "Home":
    st.markdown(
        """
        <div class="home-hero">
            <div class="product-lockup">
                <div class="product-symbol" aria-hidden="true">
                    <span></span><span></span><span></span>
                </div>
                <div>
                    <div class="home-heading">TIMAN<span class="wordmark-accent">STAT</span></div>
                    <div class="home-eyebrow">STATISTICAL SUPPORT PLATFORM</div>
                    <div class="product-byline">by Timan Analytics</div>
                </div>
            </div>
            <div class="hero-divider"></div>
            <h1 class="hero-statement">Turning data into meaningful insights.</h1>
            <p class="home-description">
                A professional platform for data management, statistical analysis,
                research and evidence-based decision-making.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-kicker">Explore the platform</div>',
        unsafe_allow_html=True,
    )
    feature_columns = st.columns(4, gap="medium")
    feature_cards = [
        (
            "01",
            "Data Management",
            "Import and organise datasets.",
            "feature-blue",
            "▤",
        ),
        (
            "02",
            "Statistical Analysis",
            "Explore data and calculate statistical summaries.",
            "feature-teal",
            "∑",
        ),
        (
            "03",
            "Survey Analysis",
            "Examine survey findings and response patterns.",
            "feature-gold",
            "▥",
        ),
        (
            "04",
            "Reporting",
            "Communicate results clearly.",
            "feature-red",
            "▧",
        ),
    ]
    for column, (number, title, description, accent, symbol) in zip(
        feature_columns, feature_cards
    ):
        with column:
            st.markdown(
                f"""
                <div class="feature-card {accent}">
                    <div class="feature-card-top">
                        <span class="feature-symbol" aria-hidden="true">{symbol}</span>
                        <span class="feature-number">{number}</span>
                    </div>
                    <div class="feature-title">{title}</div>
                    <div class="feature-description">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div class="section-kicker workspace-kicker">Your analytical workspace</div>',
        unsafe_allow_html=True,
    )
    df = st.session_state.dataset

    if df is None:
        a, b, c = st.columns(3)
        a.metric("Dataset status", "Not loaded")
        b.metric("Available formats", "CSV / Excel")
        c.metric("Workspace", "Browser session")

        st.info(
            "Start by uploading a dataset. Your data will remain available "
            "as you move between the platform's analytical modules in this session."
        )
        st.button(
            "Go to Data Management",
            type="primary",
            on_click=go_to_data_management,
        )
    else:
        a, b, c = st.columns(3)
        a.metric("Rows", f"{df.shape[0]:,}")
        b.metric("Columns", f"{df.shape[1]:,}")
        c.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")

        st.subheader("Dataset preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.caption(f"Current dataset: {st.session_state.dataset_name}")
    # ============================================================
# DATA MANAGEMENT
# ============================================================

elif page == "Data Management":
    st.title("Data Management")
    st.caption(status_text(MODULES[page][0]))

    st.write(
        "Upload a CSV or Excel workbook. For Excel files, "
        "select and preview a worksheet before importing it. "
        "The active dataset remains available as you navigate "
        "between modules in this session."
    )

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx"],
        key="dataset_uploader",
        help=(
            "Supported formats: CSV and .xlsx. "
            "Password-protected workbooks are not supported."
        ),
    )

    if uploaded_file is not None:
        upload_id = get_upload_id(uploaded_file)
        upload_key = f"{uploaded_file.name}:{upload_id}"
        file_name = uploaded_file.name.lower()
        current_user_id = st.session_state.get("user_id")
        try:
            validate_current_dataset_limits(
                file_size_bytes=len(uploaded_file.getvalue()),
            )
        except (DatasetLimitExceeded, RuntimeError) as exc:
            st.error(str(exc))
            st.stop()
        except Exception:
            st.error("Your upload allowance could not be verified. The file was not imported.")
            st.stop()

        # CSV: import directly when a different file is uploaded.
        if file_name.endswith(".csv"):
            if (
                st.session_state.dataset_source_key != upload_key
                or st.session_state.dataset is None
            ):
                try:
                    imported = load_uploaded_file(uploaded_file)
                    validate_current_dataset_limits(row_count=len(imported))

                    st.session_state.dataset = imported
                    st.session_state.dataset_name = uploaded_file.name
                    st.session_state.dataset_source_key = upload_key

                    st.success(
                        f"Successfully imported **{uploaded_file.name}**."
                    )

                except Exception as exc:
                    st.error(f"Import failed: {exc}")

            else:
                st.success(
                    f"Dataset loaded: **{uploaded_file.name}**"
                )

        # Excel: inspect worksheets and require explicit selection.
        elif file_name.endswith(".xlsx"):
            try:
                with pd.ExcelFile(
                    io.BytesIO(uploaded_file.getvalue()),
                    engine="openpyxl",
                ) as workbook:
                    sheet_names = workbook.sheet_names

                if not sheet_names:
                    st.error(
                        "This workbook does not contain any worksheets."
                    )

                else:
                    st.subheader("Select an Excel worksheet")

                    selected_sheet = st.selectbox(
                        "Worksheets in this workbook",
                        sheet_names,
                        key=f"sheet_selector_{upload_id}",
                    )

                    preview = pd.read_excel(
                        io.BytesIO(uploaded_file.getvalue()),
                        sheet_name=selected_sheet,
                        engine="openpyxl",
                        nrows=10,
                    )

                    st.write(
                        f"Worksheet preview: **{selected_sheet}**"
                    )

                    st.dataframe(
                        preview,
                        hide_index=True,
                        use_container_width=True,
                    )

                    st.caption(
                        "Before importing, check the column headings "
                        "and records. Avoid worksheets containing only "
                        "pivot tables, subtotals or grand totals."
                    )

                    if st.button(
                        "Load selected worksheet",
                        type="primary",
                        key=f"load_sheet_{upload_id}",
                    ):
                        imported = load_uploaded_file(
                            uploaded_file,
                            sheet_name=selected_sheet,
                        )
                        validate_current_dataset_limits(row_count=len(imported))

                        st.session_state.dataset = imported
                        st.session_state.dataset_name = (
                            f"{uploaded_file.name} — {selected_sheet}"
                        )
                        st.session_state.dataset_source_key = (
                            f"{upload_key}:{selected_sheet}"
                        )

                        st.success(
                            f"Imported worksheet **{selected_sheet}** "
                            f"from **{uploaded_file.name}**."
                        )

            except Exception as exc:
                st.error(f"Excel import failed: {exc}")

    # Show the active dataset, whether or not a new file is being previewed.
    df = st.session_state.dataset

    if df is not None:
        st.divider()
        st.subheader("Currently loaded dataset")

        st.caption(
            f"Active dataset: {st.session_state.dataset_name}"
        )

        a, b, c = st.columns(3)

        a.metric("Rows", f"{df.shape[0]:,}")
        b.metric("Columns", f"{df.shape[1]:,}")
        c.metric(
            "Missing cells",
            f"{int(df.isna().sum().sum()):,}",
        )

        st.dataframe(
            df.head(100),
            use_container_width=True,
        )

        with st.expander("Column details"):
            details = pd.DataFrame(
                {
                    "Column": df.columns.astype(str),
                    "Data type": [
                        str(dtype) for dtype in df.dtypes
                    ],
                    "Missing values": [
                        int(value)
                        for value in df.isna().sum().values
                    ],
                    "Unique values": [
                        int(df[col].nunique(dropna=True))
                        for col in df.columns
                    ],
                }
            )

            st.dataframe(
                details,
                hide_index=True,
                use_container_width=True,
            )

        quota_download_button(
            "Download current dataset as CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_dataset_export.csv",
            mime="text/csv",
            key="download_dataset_management",
        )

    else:
        st.info(
            "No dataset loaded yet. Choose a file above to get started."
        )


# ============================================================
# DATA QUALITY
# ============================================================

elif page == "Data Quality":
    st.title("Data Quality")
    st.caption(status_text(MODULES[page][0]))
    st.write(
        "Assess completeness, uniqueness, consistency and potential "
        "numeric anomalies before using the dataset for reporting or "
        "statistical analysis. Checks flag issues for review; they do "
        "not automatically change or delete source data."
    )

    df = get_dataset()

    if df is not None:
        row_count, column_count = df.shape
        missing_cells = int(df.isna().sum().sum())
        total_cells = row_count * column_count
        duplicate_rows = int(df.duplicated().sum())
        blank_cells = 0

        for col in df.columns:
            if (
                pd.api.types.is_object_dtype(df[col].dtype)
                or pd.api.types.is_string_dtype(df[col].dtype)
            ):
                blank_cells += int(
                    df[col].dropna().astype(str).str.strip().eq("").sum()
                )

        all_empty_columns = [
            str(col) for col in df.columns
            if df[col].isna().all()
        ]
        constant_columns = [
            str(col) for col in df.columns
            if df[col].nunique(dropna=True) <= 1
        ]
        completeness = (
            (total_cells - missing_cells - blank_cells) / total_cells * 100
            if total_cells else 0.0
        )

        st.subheader("Dataset-level quality overview")
        a, b, c, d = st.columns(4)
        a.metric("Records", f"{row_count:,}")
        b.metric("Variables", f"{column_count:,}")
        c.metric("Exact duplicate rows", f"{duplicate_rows:,}")
        d.metric("Overall completeness", f"{completeness:.1f}%")

        e, f, g = st.columns(3)
        e.metric("Missing cells", f"{missing_cells:,}")
        f.metric("Blank text cells", f"{blank_cells:,}")
        g.metric(
            "Potentially constant variables",
            f"{len(constant_columns):,}",
        )

        st.caption(
            "Overall completeness treats empty text strings as incomplete "
            "in addition to explicitly missing values. Duplicate records "
            "are exact row matches; they may or may not be errors depending "
            "on the dataset's unit of analysis."
        )

        st.subheader("Variable-level quality profile")
        quality = variable_quality_profile(df)
        st.dataframe(quality, hide_index=True, use_container_width=True)
        quota_download_button(
            "Download variable quality profile",
            data=quality.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_data_quality_profile.csv",
            mime="text/csv",
            key="download_quality_profile",
        )

        st.subheader("Missingness by variable")
        missing_by_variable = pd.DataFrame({
            "Variable": [str(col) for col in df.columns],
            "Missing values": [int(df[col].isna().sum()) for col in df.columns],
            "Missing (%)": [
                round(float(df[col].isna().mean() * 100), 2)
                if row_count else 0.0
                for col in df.columns
            ],
        })
        missing_by_variable = missing_by_variable.sort_values(
            "Missing (%)", ascending=False
        )
        if missing_by_variable["Missing values"].sum() == 0:
            st.success("No explicitly missing values were detected.")
        else:
            st.bar_chart(
                missing_by_variable.set_index("Variable")[["Missing (%)"]]
            )
            st.dataframe(
                missing_by_variable,
                hide_index=True,
                use_container_width=True,
            )
        quota_download_button(
            "Download missingness report",
            data=missing_by_variable.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_missingness_report.csv",
            mime="text/csv",
            key="download_missingness_report",
        )

        st.subheader("Duplicate record review")
        st.write(
            "Exact duplicates are rows where every column matches another "
            "row. Review them against the data collection process before "
            "deciding whether they should be removed."
        )
        if duplicate_rows:
            show_duplicates = st.checkbox(
                "Show exact duplicate rows",
                value=False,
                key="show_duplicate_rows",
            )
            if show_duplicates:
                duplicate_mask = df.duplicated(keep=False)
                st.dataframe(
                    df.loc[duplicate_mask],
                    use_container_width=True,
                )
                quota_download_button(
                    "Download rows involved in exact duplicates",
                    data=df.loc[duplicate_mask].to_csv(index=False).encode("utf-8-sig"),
                    file_name="timan_duplicate_rows_review.csv",
                    mime="text/csv",
                    key="download_duplicate_rows",
                )
        else:
            st.success("No exact duplicate rows were detected.")

        st.subheader("Potential numeric outliers")
        st.write(
            "The 1.5 × IQR rule flags values outside the lower and upper "
            "fences. These are review flags, not proof that a value is wrong."
        )
        outlier_profile = numeric_outlier_profile(df)
        if outlier_profile.empty:
            st.info("No numeric columns are available for IQR outlier checks.")
        else:
            st.dataframe(
                outlier_profile,
                hide_index=True,
                use_container_width=True,
            )
            quota_download_button(
                "Download potential outlier summary",
                data=outlier_profile.to_csv(index=False).encode("utf-8-sig"),
                file_name="timan_potential_outliers.csv",
                mime="text/csv",
                key="download_outlier_profile",
            )

        st.subheader("Quality review notes")
        notes = []
        if missing_cells:
            notes.append(
                f"Review missing values in {int((df.isna().sum() > 0).sum())} "
                "variable(s); determine whether missingness has a known reason."
            )
        if blank_cells:
            notes.append(
                f"Found {blank_cells:,} blank or whitespace-only text cell(s). "
                "These may need to be standardised as missing values."
            )
        if duplicate_rows:
            notes.append(
                f"Review {duplicate_rows:,} exact duplicate row(s) against "
                "the intended unit of analysis."
            )
        if all_empty_columns:
            notes.append(
                "Entirely empty variables: " + ", ".join(all_empty_columns) + "."
            )
        if constant_columns:
            notes.append(
                "Variables with one or zero observed unique values: "
                + ", ".join(constant_columns)
                + ". Confirm whether they are useful for analysis."
            )
        if notes:
            for note in notes:
                st.warning(note)
        else:
            st.success(
                "These initial checks did not identify missing cells, blank "
                "text cells, exact duplicate rows or constant variables. "
                "This is not a guarantee that the dataset is error-free."
            )

        st.info(
            "Scope limitation: these checks do not verify values against an "
            "external source, questionnaire skip logic, valid ranges, unique "
            "respondent IDs, or programme-specific indicator rules. Those "
            "checks require context and validation rules for the dataset."
        )
        # ============================================================
# SURVEY ANALYSIS
# ============================================================

elif page == "Survey Analysis":
    st.title("Survey Analysis")
    st.caption(status_text(MODULES[page][0]))
    st.write(
        "TimanStat first inspects the imported dataset for questionnaire-style "
        "structure, respondent records, response types and missing-response "
        "patterns. Recognition is advisory; confirm the findings against the "
        "questionnaire and codebook before proceeding."
    )

    df = get_dataset()

    if df is not None:
        result = run_survey_profile(df)
        metadata = result.metadata

        if metadata["is_survey_like"]:
            st.success(
                f"Questionnaire-style structure detected "
                f"({metadata['confidence']} confidence)."
            )
        else:
            st.warning(
                "The dataset has not yet been confidently recognised as "
                "questionnaire-style data. You can still inspect the profile "
                "and confirm its structure."
            )

        metric_columns = st.columns(3)
        metric_columns[0].metric("Respondent records", f"{metadata['respondents']:,}")
        metric_columns[1].metric("Variables", f"{metadata['variable_count']:,}")
        metric_columns[2].metric("Response-like variables", f"{metadata['question_count']:,}")

        st.subheader("Response variable profile")
        profile_table = result.tables["response_variable_profile"]
        if profile_table.empty:
            st.info("No variables are available to profile.")
        else:
            st.dataframe(profile_table, hide_index=True, use_container_width=True)

        response_counts = metadata.get("response_type_counts", {})
        if response_counts:
            st.subheader("Detected response structures")
            st.dataframe(
                pd.DataFrame(
                    [{"Response structure": key, "Variables": value}
                     for key, value in response_counts.items()]
                ),
                hide_index=True,
                use_container_width=True,
            )

        if metadata.get("identifier_candidates"):
            st.caption(
                "Possible record identifiers: "
                + ", ".join(metadata["identifier_candidates"])
                + ". These are name-based suggestions, not verified unique IDs."
            )

        st.subheader("Interpretation and safeguards")
        for finding in result.findings:
            st.write(f"• {finding}")
        for warning in result.limitations:
            st.warning(warning)

        st.subheader("Question-level response frequencies")
        frequency_columns = metadata.get("frequency_columns", [])
        if frequency_columns:
            selected_question = st.selectbox(
                "Choose a question",
                frequency_columns,
                key="survey_frequency_question",
            )
            st.dataframe(
                result.tables[f"frequency::{selected_question}"],
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Percentages use all imported records as the denominator; "
                "missing responses are shown separately."
            )
        else:
            st.info(
                "No categorical or recognised scale questions are available "
                "for frequency tabulation."
            )

        st.subheader("Multiple-response questions")
        multiple_columns = metadata.get("multiple_response_columns", [])
        if multiple_columns:
            selected_multiple = st.selectbox(
                "Choose a multiple-response question",
                multiple_columns,
                key="survey_multiple_response_question",
            )
            multiple_table = result.tables[f"multiple_response::{selected_multiple}"]
            answered = multiple_table.attrs.get("respondents_with_selection", 0)
            st.metric("Respondents selecting at least one option", f"{answered:,}")
            st.dataframe(
                multiple_table,
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Each respondent is counted once per selected option. "
                "Percentages use respondents with at least one recorded selection; "
                "they can therefore add up to more than 100%."
            )
        else:
            st.info(
                "No delimited multiple-response questions were detected. "
                "If the questionnaire stores each option in a separate column, "
                "that structure needs a separate checkbox-matrix recogniser."
            )

        st.subheader("Likert item analysis")
        likert_columns = metadata.get("likert_columns", [])
        if likert_columns:
            selected_likert = st.selectbox(
                "Choose a recognised Likert question",
                likert_columns,
                key="survey_likert_question",
            )
            likert_table = result.tables[f"likert::{selected_likert}"]
            likert_summary = likert_table.attrs
            summary_columns = st.columns(4)
            summary_columns[0].metric("Valid responses", f"{likert_summary['valid_n']:,}")
            summary_columns[1].metric("Missing responses", f"{likert_summary['missing_n']:,}")
            summary_columns[2].metric(
                "Median response",
                str(likert_summary["median_response"])
                if likert_summary["median_response"] is not None else "—",
            )
            summary_columns[3].metric(
                "Mode",
                ", ".join(map(str, likert_summary["mode_responses"])) or "—",
            )
            st.dataframe(
                likert_table,
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Responses are displayed in the recognised ordinal order. "
                "Percentages are shown among valid responses and among all records. "
                "The median is reported as an ordered response category; no mean "
                "score or positive/negative direction is assumed."
            )
        else:
            st.info(
                "No recognised labelled Likert items are available. Numeric or "
                "custom-coded scales must be confirmed against the questionnaire "
                "or codebook before they can be analysed as ordinal responses."
            )

        st.divider()
        st.subheader("Survey-weighted descriptive estimates")
        st.write(
            "Use a documented positive survey-weight variable to estimate "
            "weighted response distributions or numeric summaries. Confirm "
            "that the weights match the target population and unit of analysis."
        )
        numeric_weight_candidates = [
            column for column in df.select_dtypes(include="number").columns
        ]
        if not numeric_weight_candidates:
            st.info(
                "No numeric columns are available for a survey weight. "
                "Import the documented weight variable as numeric data."
            )
        else:
            selected_weight = st.selectbox(
                "Survey weight variable",
                numeric_weight_candidates,
                key="survey_weight_variable",
            )
            weighted_analysis_type = st.radio(
                "Weighted estimate",
                ["Categorical frequencies", "Numeric summary"],
                horizontal=True,
                key="survey_weighted_analysis_type",
            )
            if weighted_analysis_type == "Categorical frequencies":
                weighted_outcome_candidates = [
                    column for column in df.columns if column != selected_weight
                ]
            else:
                weighted_outcome_candidates = [
                    column for column in df.select_dtypes(include="number").columns
                    if column != selected_weight
                ]
            if not weighted_outcome_candidates:
                st.info(
                    "No eligible outcome variable is available for the selected "
                    "weighted analysis."
                )
            else:
                selected_weighted_outcome = st.selectbox(
                    "Outcome variable",
                    weighted_outcome_candidates,
                    key="survey_weighted_outcome",
                )
                include_weighted_missing = False
                if weighted_analysis_type == "Categorical frequencies":
                    include_weighted_missing = st.checkbox(
                        "Include missing responses as a separate category",
                        value=False,
                        key="survey_weighted_include_missing",
                    )
                if st.button(
                    "Calculate weighted estimates",
                    type="primary",
                    key="run_survey_weighted_estimates",
                ):
                    try:
                        if weighted_analysis_type == "Categorical frequencies":
                            weighted_result = run_weighted_frequency_service(
                                df,
                                selected_weighted_outcome,
                                selected_weight,
                                include_weighted_missing,
                            )
                            weighted_table = weighted_result.tables["weighted_frequencies"]
                        else:
                            weighted_result = run_weighted_numeric_summary_service(
                                df,
                                selected_weighted_outcome,
                                selected_weight,
                            )
                            weighted_table = weighted_result.tables["weighted_summary"]
                        st.session_state["survey_weighted_result"] = weighted_result
                        st.session_state["survey_weighted_result_key"] = (
                            _dataset_analysis_key(df),
                            selected_weight,
                            selected_weighted_outcome,
                            weighted_analysis_type,
                            include_weighted_missing,
                        )
                    except (TypeError, ValueError, KeyError) as exc:
                        st.error(str(exc))
                expected_weighted_key = (
                    _dataset_analysis_key(df),
                    selected_weight,
                    selected_weighted_outcome,
                    weighted_analysis_type,
                    include_weighted_missing,
                )
                saved_weighted_result = st.session_state.get("survey_weighted_result")
                if (
                    saved_weighted_result is not None
                    and st.session_state.get("survey_weighted_result_key") == expected_weighted_key
                ):
                    weighted_metadata = saved_weighted_result.metadata
                    metric_row = st.columns(4)
                    metric_row[0].metric("Records analysed", f"{weighted_metadata['records_used']:,}")
                    metric_row[1].metric("Sum of weights", f"{weighted_metadata['sum_of_weights']:,.3f}")
                    metric_row[2].metric(
                        "Kish effective N",
                        f"{weighted_metadata['effective_sample_size_kish']:.1f}",
                    )
                    metric_row[3].metric(
                        "Weight range",
                        f"{weighted_metadata['minimum_weight']:.3g}–{weighted_metadata['maximum_weight']:.3g}",
                    )
                    st.dataframe(
                        saved_weighted_result.tables[
                            "weighted_frequencies"
                            if weighted_analysis_type == "Categorical frequencies"
                            else "weighted_summary"
                        ],
                        hide_index=True,
                        use_container_width=True,
                    )
                    for finding in saved_weighted_result.findings:
                        st.write(f"• {finding}")
                    for warning in saved_weighted_result.limitations:
                        st.warning(warning)
                    st.caption(
                        "Weighted results are descriptive estimates only. "
                        "No design-adjusted standard errors, confidence intervals "
                        "or hypothesis tests are produced in this release."
                    )

        st.divider()
        st.subheader("Stratified survey estimates")
        st.write(
            "Estimate weighted means or category proportions while accounting "
            "for stratification. This release requires expansion weights that "
            "are constant within each stratum and independent simple random "
            "sampling within strata."
        )
        strat_numeric_columns = list(df.select_dtypes(include="number").columns)
        if not strat_numeric_columns:
            st.info("A numeric expansion-weight variable is required.")
        else:
            strat_weight = st.selectbox(
                "Expansion weight", strat_numeric_columns,
                key="stratified_weight_variable",
            )
            strat_candidates = [c for c in df.columns if c != strat_weight]
            strat_variable = st.selectbox(
                "Stratum identifier", strat_candidates,
                key="stratified_stratum_variable",
            )
            strat_outcome_type = st.radio(
                "Stratified outcome", ["Numeric mean", "Categorical proportion"],
                horizontal=True, key="stratified_outcome_type",
            )
            if strat_outcome_type == "Numeric mean":
                strat_outcomes = [
                    c for c in strat_numeric_columns
                    if c not in (strat_weight, strat_variable)
                ]
            else:
                strat_outcomes = [
                    c for c in df.columns
                    if c not in (strat_weight, strat_variable)
                ]
            if not strat_outcomes:
                st.info("No eligible outcome variable is available for this estimate.")
            else:
                strat_outcome = st.selectbox(
                    "Outcome variable", strat_outcomes,
                    key="stratified_outcome_variable",
                )
                strat_confidence = st.selectbox(
                    "Confidence level", [0.90, 0.95, 0.99], index=1,
                    format_func=lambda value: f"{value:.0%}",
                    key="stratified_confidence_level",
                )
                if st.button(
                    "Calculate stratified estimate", type="primary",
                    key="run_stratified_estimate",
                ):
                    try:
                        if strat_outcome_type == "Numeric mean":
                            strat_result = run_stratified_weighted_mean_service(
                                df, strat_outcome, strat_weight,
                                strat_variable, strat_confidence,
                            )
                            strat_table_key = "stratified_estimate"
                        else:
                            strat_result = run_stratified_weighted_frequency_service(
                                df, strat_outcome, strat_weight,
                                strat_variable, strat_confidence,
                            )
                            strat_table_key = "stratified_frequencies"
                        st.session_state["stratified_survey_result"] = strat_result
                        st.session_state["stratified_survey_result_key"] = (
                            _dataset_analysis_key(df), strat_outcome, strat_weight,
                            strat_variable, strat_outcome_type, strat_confidence,
                        )
                    except (TypeError, ValueError, KeyError) as exc:
                        st.error(str(exc))
                strat_key = (
                    _dataset_analysis_key(df), strat_outcome, strat_weight,
                    strat_variable, strat_outcome_type, strat_confidence,
                )
                saved_strat_result = st.session_state.get("stratified_survey_result")
                if (
                    saved_strat_result is not None
                    and st.session_state.get("stratified_survey_result_key") == strat_key
                ):
                    st.dataframe(
                        saved_strat_result.tables[
                            "stratified_estimate"
                            if strat_outcome_type == "Numeric mean"
                            else "stratified_frequencies"
                        ],
                        hide_index=True, use_container_width=True,
                    )
                    with st.expander("Stratum-level sample and weight summary"):
                        st.dataframe(
                            saved_strat_result.tables["strata_summary"],
                            hide_index=True, use_container_width=True,
                        )
                    for finding in saved_strat_result.findings:
                        st.write(f"• {finding}")
                    for warning in saved_strat_result.limitations:
                        st.warning(warning)
                    st.caption(
                        "Confidence intervals use a stratified simple-random-sample "
                        "variance estimator without finite population correction. "
                        "PSU clustering and multistage designs are not yet supported."
                    )

        st.divider()
        st.subheader("Cluster-adjusted survey estimates")
        st.write(
            "Account for correlation among respondents sampled within the same "
            "primary sampling unit (PSU), optionally retaining stratification. "
            "Use the PSU identifier from the sampling design, not an arbitrary "
            "geographic or administrative label."
        )
        cluster_numeric = list(df.select_dtypes(include="number").columns)
        cluster_cols = list(df.columns)
        if not cluster_numeric or len(cluster_cols) < 3:
            st.info("A numeric weight, an outcome and a PSU identifier are required.")
        else:
            cluster_weight = st.selectbox(
                "Survey weight", cluster_numeric, key="cluster_weight_variable"
            )
            cluster_id_candidates = [c for c in cluster_cols if c != cluster_weight]
            cluster_id = st.selectbox(
                "Primary sampling unit (PSU)", cluster_id_candidates,
                key="cluster_psu_variable",
            )
            cluster_use_strata = st.checkbox(
                "My sample is stratified", value=True, key="cluster_use_strata"
            )
            if cluster_use_strata:
                cluster_strata_candidates = [
                    c for c in cluster_cols
                    if c not in (cluster_weight, cluster_id)
                ]
                cluster_strata = st.selectbox(
                    "Stratum identifier", cluster_strata_candidates,
                    key="cluster_strata_variable",
                )
            else:
                cluster_strata = None
            cluster_outcome_type = st.radio(
                "Cluster-adjusted outcome", ["Numeric mean", "Categorical proportion"],
                horizontal=True, key="cluster_outcome_type",
            )
            excluded_cluster = [cluster_weight, cluster_id]
            if cluster_strata:
                excluded_cluster.append(cluster_strata)
            if cluster_outcome_type == "Numeric mean":
                cluster_outcomes = [
                    c for c in cluster_numeric if c not in excluded_cluster
                ]
            else:
                cluster_outcomes = [
                    c for c in cluster_cols if c not in excluded_cluster
                ]
            if not cluster_outcomes:
                st.info("No eligible outcome variable is available.")
            else:
                cluster_outcome = st.selectbox(
                    "Outcome variable", cluster_outcomes,
                    key="cluster_outcome_variable",
                )
                cluster_confidence = st.selectbox(
                    "Confidence level", [0.90, 0.95, 0.99], index=1,
                    format_func=lambda value: f"{value:.0%}",
                    key="cluster_confidence_level",
                )
                if st.button(
                    "Calculate cluster-adjusted estimate", type="primary",
                    key="run_cluster_survey_estimate",
                ):
                    try:
                        if cluster_outcome_type == "Numeric mean":
                            cluster_result = run_cluster_weighted_mean_service(
                                df, cluster_outcome, cluster_weight, cluster_id,
                                cluster_strata, cluster_confidence,
                            )
                            cluster_table_key = "cluster_estimate"
                        else:
                            cluster_result = run_cluster_weighted_frequency_service(
                                df, cluster_outcome, cluster_weight, cluster_id,
                                cluster_strata, cluster_confidence,
                            )
                            cluster_table_key = "cluster_frequencies"
                        st.session_state["cluster_survey_result"] = cluster_result
                        st.session_state["cluster_survey_result_key"] = (
                            _dataset_analysis_key(df), cluster_outcome,
                            cluster_weight, cluster_id, cluster_strata,
                            cluster_outcome_type, cluster_confidence,
                        )
                    except (TypeError, ValueError, KeyError) as exc:
                        st.error(str(exc))
                cluster_key = (
                    _dataset_analysis_key(df), cluster_outcome, cluster_weight,
                    cluster_id, cluster_strata, cluster_outcome_type,
                    cluster_confidence,
                )
                saved_cluster_result = st.session_state.get("cluster_survey_result")
                if (
                    saved_cluster_result is not None
                    and st.session_state.get("cluster_survey_result_key") == cluster_key
                ):
                    st.dataframe(
                        saved_cluster_result.tables[
                            "cluster_estimate"
                            if cluster_outcome_type == "Numeric mean"
                            else "cluster_frequencies"
                        ],
                        hide_index=True, use_container_width=True,
                    )
                    for finding in saved_cluster_result.findings:
                        st.write(f"• {finding}")
                    for warning in saved_cluster_result.limitations:
                        st.warning(warning)
                    st.caption(
                        "Variance is estimated from independent sampled PSUs "
                        "using a with-replacement ultimate-cluster method. "
                        "At least two PSUs per stratum are required."
                    )

        st.divider()
        st.subheader("Two-stage survey design inspection")
        st.write(
            "Validate a two-stage sample hierarchy: respondents or sampled "
            "secondary units (SSUs) nested within primary sampling units (PSUs). "
            "This tool checks design metadata and optional stage sampling "
            "fractions; it does not yet calculate multistage standard errors."
        )
        ms_numeric = list(df.select_dtypes(include="number").columns)
        ms_cols = list(df.columns)
        if len(ms_cols) < 3 or not ms_numeric:
            st.info("A numeric final weight, PSU identifier and SSU identifier are required.")
        else:
            ms_weight = st.selectbox(
                "Final survey weight", ms_numeric, key="multistage_weight"
            )
            ms_psu_options = [x for x in ms_cols if x != ms_weight]
            ms_psu = st.selectbox(
                "First-stage unit (PSU)", ms_psu_options, key="multistage_psu"
            )
            ms_ssu_options = [
                x for x in ms_cols if x not in (ms_weight, ms_psu)
            ]
            ms_ssu = st.selectbox(
                "Second-stage unit (SSU)", ms_ssu_options, key="multistage_ssu"
            )
            ms_use_strata = st.checkbox(
                "The first-stage sample is stratified",
                value=True, key="multistage_use_strata",
            )
            if ms_use_strata:
                ms_strata_options = [
                    x for x in ms_cols if x not in (ms_weight, ms_psu, ms_ssu)
                ]
                ms_strata = st.selectbox(
                    "Stratum identifier", ms_strata_options,
                    key="multistage_strata",
                ) if ms_strata_options else None
            else:
                ms_strata = None
            ms_remaining = [
                x for x in ms_numeric
                if x not in (ms_weight, ms_psu, ms_ssu, ms_strata)
            ]
            ms_use_psu_population = st.checkbox(
                "I have the population number of PSUs in each stratum",
                value=False, key="multistage_use_psu_population",
            )
            ms_psu_population = None
            if ms_use_psu_population:
                if ms_remaining:
                    ms_psu_population = st.selectbox(
                        "Population PSU count per stratum",
                        ms_remaining, key="multistage_psu_population",
                    )
                else:
                    st.info("No unused numeric variable is available for PSU population counts.")
            ms_ssu_remaining = [
                x for x in ms_remaining if x != ms_psu_population
            ]
            ms_use_ssu_population = st.checkbox(
                "I have the population number of SSUs in each PSU",
                value=False, key="multistage_use_ssu_population",
            )
            ms_ssu_population = None
            if ms_use_ssu_population:
                if ms_ssu_remaining:
                    ms_ssu_population = st.selectbox(
                        "Population SSU count per PSU",
                        ms_ssu_remaining, key="multistage_ssu_population",
                    )
                else:
                    st.info("No unused numeric variable is available for SSU population counts.")
            ms_design_key = (
                _dataset_analysis_key(df), ms_weight, ms_psu, ms_ssu,
                ms_strata, ms_psu_population, ms_ssu_population,
            )
            if st.button(
                "Validate two-stage sample design",
                type="primary", key="run_multistage_design_inspection",
            ):
                try:
                    ms_result = run_two_stage_survey_design_inspection_service(
                        df, ms_psu, ms_ssu, ms_weight, ms_strata,
                        ms_psu_population, ms_ssu_population,
                    )
                    st.session_state["multistage_design_result"] = ms_result
                    st.session_state["multistage_design_result_key"] = ms_design_key
                except (TypeError, ValueError, KeyError) as exc:
                    st.error(str(exc))
            saved_ms_result = st.session_state.get("multistage_design_result")
            if (
                saved_ms_result is not None
                and st.session_state.get("multistage_design_result_key") == ms_design_key
            ):
                st.dataframe(
                    saved_ms_result.tables["psu_summary"],
                    hide_index=True, use_container_width=True,
                )
                with st.expander("Secondary sampling unit summary"):
                    st.dataframe(
                        saved_ms_result.tables["ssu_summary"],
                        hide_index=True, use_container_width=True,
                    )
                for finding in saved_ms_result.findings:
                    st.write(f"• {finding}")
                for warning in saved_ms_result.limitations:
                    st.warning(warning)

            st.divider()
            st.subheader("Two-stage design-based population total")
            st.write(
                "Estimate a population total using a two-stage Taylor variance "
                "estimator with finite population corrections (FPCs) at both "
                "sampling stages. This requires one row per sampled SSU, where "
                "the outcome is the fully enumerated total for that SSU."
            )
            if ms_psu_population is None or ms_ssu_population is None:
                st.warning(
                    "Select both population PSU counts per stratum and population "
                    "SSU counts per PSU above before running design-based estimation."
                )
            else:
                outcome_options = [
                    x for x in ms_numeric
                    if x not in (
                        ms_weight, ms_psu_population, ms_ssu_population,
                    )
                ]
                if ms_strata in outcome_options:
                    outcome_options.remove(ms_strata)
                if outcome_options:
                    ms_outcome = st.selectbox(
                        "SSU outcome total", outcome_options,
                        key="multistage_total_outcome",
                    )
                    ms_confidence = st.selectbox(
                        "Confidence level", [0.90, 0.95, 0.99],
                        index=1, format_func=lambda x: f"{x:.0%}",
                        key="multistage_total_confidence",
                    )
                    ms_total_key = (
                        _dataset_analysis_key(df), ms_outcome, ms_psu, ms_ssu,
                        ms_strata, ms_psu_population, ms_ssu_population,
                        ms_confidence,
                    )
                    if st.button(
                        "Estimate two-stage population total",
                        type="primary", key="run_two_stage_total",
                    ):
                        try:
                            total_result = run_two_stage_survey_total_service(
                                df, ms_outcome, ms_psu, ms_ssu,
                                ms_psu_population, ms_ssu_population,
                                ms_strata, ms_confidence,
                            )
                            st.session_state["two_stage_total_result"] = total_result
                            st.session_state["two_stage_total_result_key"] = ms_total_key
                        except (TypeError, ValueError, KeyError) as exc:
                            st.error(str(exc))
                    saved_total = st.session_state.get("two_stage_total_result")
                    if (
                        saved_total is not None
                        and st.session_state.get("two_stage_total_result_key") == ms_total_key
                    ):
                        st.metric(
                            "Estimated population total",
                            f"{saved_total.metadata['estimate']:,.4g}",
                        )
                        st.metric(
                            "Design-based standard error",
                            f"{saved_total.metadata['standard_error']:,.4g}",
                        )
                        ci = saved_total.metadata["confidence_interval"]
                        st.write(
                            f"{ms_confidence:.0%} confidence interval: "
                            f"[{ci[0]:,.4g}, {ci[1]:,.4g}]"
                        )
                        st.dataframe(
                            saved_total.tables["stratum_estimates"],
                            hide_index=True, use_container_width=True,
                        )
                        with st.expander("PSU-level expansion and sampling details"):
                            st.dataframe(
                                saved_total.tables["psu_details"],
                                hide_index=True, use_container_width=True,
                            )
                        for finding in saved_total.findings:
                            st.write(f"• {finding}")
                        for warning in saved_total.limitations:
                            st.warning(warning)
                else:
                    st.info("No eligible numeric SSU outcome variable is available.")

        st.info(
            "Unweighted question-level frequencies above describe the imported "
            "records. Use the weighted estimator separately when a documented "
            "survey weight is available. Complex-design inference is not yet "
            "supported."
        )
    else:
        st.info("Upload and import a survey dataset in Data Management to begin.")


# ============================================================
# DESCRIPTIVE STATISTICS
# ============================================================

elif page == "Descriptive Statistics":
    st.title("Descriptive Statistics")
    st.caption(status_text(MODULES[page][0]))
    st.write(
        "Explore distributions, central tendency, variability and category "
        "frequencies. Results describe the loaded data; they do not establish "
        "causation or automatically account for survey weights or complex "
        "sample designs."
    )

    df = get_dataset()

    if df is not None:
        analysis_key = _dataset_analysis_key(df)
        if st.button(
            "Run descriptive analysis",
            type="primary",
            key="run_descriptive_analysis",
        ):
            try:
                if PUBLIC_ACCESS_MODE:
                    consume_public_usage("monthly_analyses")
                else:
                    user_id = st.session_state.get("user_id")
                    if not isinstance(user_id, str) or not user_id.strip():
                        raise RuntimeError(
                            "Your authenticated account could not be verified. Please sign in again."
                        )
                    consume_monthly_usage(
                        "monthly_analyses",
                        user_id=user_id,
                        organisation_id=get_active_organisation_id(),
                    )
            except (UsageLimitExceeded, RuntimeError) as exc:
                st.error(str(exc))
            except Exception:
                st.error("Your monthly analysis allowance could not be verified. No analysis was run.")
            else:
                st.session_state["timanstat_descriptive_analysis_key"] = analysis_key

        if st.session_state.get("timanstat_descriptive_analysis_key") != analysis_key:
            st.info(
                "Select **Run descriptive analysis** to calculate results. "
                "Each new run consumes one monthly analysis from your plan."
            )
        else:
            numeric_cols = list(df.select_dtypes(include="number").columns)
            categorical_cols = [
                col for col in df.columns
                if not pd.api.types.is_numeric_dtype(df[col].dtype)
            ]

            st.subheader("Dataset profile")
            a, b, c, d = st.columns(4)
            a.metric("Records", f"{len(df):,}")
            b.metric("Variables", f"{df.shape[1]:,}")
            c.metric("Numeric variables", f"{len(numeric_cols):,}")
            d.metric("Other variables", f"{len(categorical_cols):,}")

            st.caption(
                "Variable types follow the types assigned during import. A number "
                "stored as text will not be included in numeric summaries until "
                "it is appropriately converted in a future data-preparation step."
            )

            st.subheader("Numeric descriptive statistics")
            if not numeric_cols:
                st.info(
                    "No numeric columns were detected. Check whether numeric "
                    "values were imported as text."
                )
            else:
                numeric_records = []
                for col in numeric_cols:
                    series = pd.to_numeric(df[col], errors="coerce")
                    valid = series.dropna()
                    count = int(valid.count())
                    mean = valid.mean() if count else float("nan")
                    median = valid.median() if count else float("nan")
                    std = valid.std() if count > 1 else float("nan")
                    q1 = valid.quantile(0.25) if count else float("nan")
                    q3 = valid.quantile(0.75) if count else float("nan")
                    minimum = valid.min() if count else float("nan")
                    maximum = valid.max() if count else float("nan")
                    numeric_records.append({
                        "Variable": str(col),
                        "Valid n": count,
                        "Missing n": int(series.isna().sum()),
                        "Missing (%)": round(float(series.isna().mean() * 100), 2),
                        "Mean": mean,
                        "Median": median,
                        "Standard deviation": std,
                        "Variance": valid.var() if count > 1 else float("nan"),
                        "Minimum": minimum,
                        "Q1 (25%)": q1,
                        "Q3 (75%)": q3,
                        "Maximum": maximum,
                        "Range": maximum - minimum if count else float("nan"),
                        "IQR": q3 - q1 if count else float("nan"),
                        "Skewness": valid.skew() if count > 2 else float("nan"),
                        "Excess kurtosis": valid.kurt() if count > 3 else float("nan"),
                        "Coefficient of variation (%)": (
                            std / abs(mean) * 100
                            if count > 1 and pd.notna(mean) and mean != 0
                            else float("nan")
                        ),
                    })

                summary = pd.DataFrame(numeric_records)
                st.dataframe(summary, hide_index=True, use_container_width=True)
                quota_download_button(
                    "Download full numeric summary",
                    data=summary.to_csv(index=False).encode("utf-8-sig"),
                    file_name="timan_descriptive_statistics.csv",
                    mime="text/csv",
                    key="download_numeric_summary",
                )

                st.caption(
                    "Interpretation guide: the mean is sensitive to extreme values; "                "the median is more resistant. Standard deviation describes "
                    "spread around the mean; IQR describes the middle 50% of values. "
                    "Skewness and excess kurtosis are exploratory distribution "
                    "indicators and should be interpreted with sample size and plots."
                )

                st.subheader("Explore one numeric variable")
                selected_numeric = st.selectbox(
                    "Choose a numeric variable",
                    numeric_cols,
                    key="descriptive_numeric_variable",
                )
                values = pd.to_numeric(
                    df[selected_numeric], errors="coerce"
                ).dropna()
                if values.empty:
                    st.info("This variable has no valid numeric observations.")
                else:
                    left, right = st.columns(2)
                    with left:
                        st.markdown("**Distribution summary**")
                        st.write({
                            "Valid observations": int(values.count()),
                            "Mean": round(float(values.mean()), 4),
                            "Median": round(float(values.median()), 4),
                            "Mode(s)": [
                                str(value) for value in values.mode().head(5).tolist()
                            ],
                            "Minimum": float(values.min()),
                            "Maximum": float(values.max()),
                        })
                    with right:
                        st.markdown("**Selected quantiles**")
                        quantiles = values.quantile(
                            [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
                        ).rename_axis("Quantile").reset_index(name="Value")
                        quantiles["Quantile"] = (
                            quantiles["Quantile"] * 100
                        ).map(lambda value: f"P{value:g}")
                        st.dataframe(
                            quantiles,
                            hide_index=True,
                            use_container_width=True,
                        )

                    st.markdown("**Distribution by value range**")
                    if values.nunique() > 1:
                        bins = st.slider(
                            "Number of histogram bins",
                            min_value=5,
                            max_value=40,
                            value=15,
                            key="descriptive_histogram_bins",
                        )
                        hist, edges = np.histogram(values, bins=bins)
                        hist_df = pd.DataFrame({
                            "Value range": [
                                f"{edges[i]:.4g} – {edges[i + 1]:.4g}"
                                for i in range(len(hist))
                            ],
                            "Frequency": hist,
                        }).set_index("Value range")
                        st.bar_chart(hist_df)
                    else:
                        st.info(
                            "All valid observations have the same value; a histogram "
                            "would not show a meaningful distribution."
                        )

            st.divider()
            st.subheader("Categorical frequency analysis")
            if not categorical_cols:
                st.info("No non-numeric variables were detected.")
            else:
                selected_col = st.selectbox(
                    "Select a categorical variable",
                    categorical_cols,
                    format_func=str,
                    key="descriptive_categorical_variable",
                )
                include_missing = st.checkbox(
                    "Include missing and blank values in the frequency table",
                    value=True,
                    key="descriptive_include_missing",
                )
                series = df[selected_col].astype("object")
                blank_mask = series.notna() & series.astype(str).str.strip().eq("")
                series = series.mask(blank_mask, "(Blank text)")
                if include_missing:
                    series = series.where(series.notna(), "(Missing)")
                    denominator = len(series)
                    counts = series.value_counts(dropna=False)
                else:
                    series = series[series.notna() & ~blank_mask]
                    denominator = len(series)
                    counts = series.value_counts(dropna=True)

                frequencies = counts.rename_axis("Category").reset_index(
                    name="Frequency"
                )
                frequencies["Percentage (%)"] = (
                    (frequencies["Frequency"] / denominator * 100).round(2)
                    if denominator else 0.0
                )
                frequencies["Cumulative (%)"] = (
                    frequencies["Percentage (%)"].cumsum().round(2)
                )
                st.dataframe(
                    frequencies,
                    hide_index=True,
                    use_container_width=True,
                )
                st.caption(
                    f"Percentage denominator: {denominator:,} records. "
                    "Cumulative percentages follow the displayed frequency order. "
                    "If the variable has many unique values, the table may be long."
                )
                quota_download_button(
                    "Download categorical frequency table",
                    data=frequencies.to_csv(index=False).encode("utf-8-sig"),
                    file_name="timan_frequency_table.csv",
                    mime="text/csv",
                    key="download_frequency_table",
                )

            st.divider()
            st.subheader("Grouped numeric summaries")
            if numeric_cols and categorical_cols:
                group_col = st.selectbox(
                    "Group records by",
                    categorical_cols,
                    key="descriptive_group_column",
                )
                measure_col = st.selectbox(
                    "Summarise numeric variable",
                    numeric_cols,
                    key="descriptive_group_measure",
                )
                group_df = pd.DataFrame({
                    "Group": df[group_col].astype("object").where(
                        df[group_col].notna(), "(Missing)"
                    ).astype(str),
                    "Value": pd.to_numeric(df[measure_col], errors="coerce"),
                })
                grouped = group_df.groupby("Group", dropna=False)["Value"].agg(
                    ["count", "mean", "median", "std", "min", "max"]
                ).reset_index()
                grouped = grouped.rename(columns={
                    "count": "Valid n",
                    "mean": "Mean",
                    "median": "Median",
                    "std": "Standard deviation",
                    "min": "Minimum",
                    "max": "Maximum",
                })
                st.dataframe(grouped, hide_index=True, use_container_width=True)
                st.caption(
                    "Grouped summaries are descriptive comparisons only. Differences "
                    "between groups do not, by themselves, demonstrate that group "
                    "membership caused the observed outcome."
                )
                quota_download_button(
                    "Download grouped summary",
                    data=grouped.to_csv(index=False).encode("utf-8-sig"),
                    file_name="timan_grouped_descriptive_summary.csv",
                    mime="text/csv",
                    key="download_grouped_summary",
                )
            else:
                st.info(
                    "Grouped summaries require at least one numeric variable and "
                    "one non-numeric grouping variable."
                )

            st.divider()
            st.subheader("Exploratory correlation matrix")
            if len(numeric_cols) >= 2:
                corr_method = st.selectbox(
                    "Correlation method",
                    ["Pearson", "Spearman", "Kendall"],
                    key="descriptive_correlation_method",
                )
                corr = df[numeric_cols].corr(method=corr_method.lower())
                st.dataframe(corr.round(3), use_container_width=True)
                st.caption(
                    "Correlation describes the strength and direction of association "
                    "between numeric variables. It does not establish causation; "
                    "Pearson measures linear association, while Spearman and Kendall "
                    "are rank-based measures."
                )
                quota_download_button(
                    "Download correlation matrix",
                    data=corr.to_csv().encode("utf-8-sig"),
                    file_name="timan_correlation_matrix.csv",
                    mime="text/csv",
                    key="download_correlation_matrix",
                )
            else:
                st.info(
                    "A correlation matrix requires at least two numeric variables."
                )
                # ============================================================
            st.divider()
            render_categorical_comparison(df)
            st.divider()
            render_numeric_group_comparison(df)
            st.divider()
            render_numeric_association(df)
            st.divider()
            render_simple_linear_regression(df)
            st.divider()
            render_multiple_linear_regression(df)
            st.divider()
            render_categorical_model_recommender(df)
            st.divider()
            render_binary_logistic_regression(df)
            st.divider()
            render_multinomial_logistic_regression(df)
            st.divider()
            render_ordinal_logistic_regression(df)
            st.divider()
            render_poisson_regression(df)
            st.divider()
            render_negative_binomial_regression(df)
            st.divider()
            render_kaplan_meier_analysis(df)
            st.divider()
            render_cox_survival_regression(df)


# VISUALISATIONS
# ============================================================

elif page == "Visualisations":
    st.title("Visualisations")
    st.caption(status_text(MODULES[page][0]))

    df = get_dataset()

    if df is not None:
        numeric_cols = list(
            df.select_dtypes(include="number").columns
        )
        all_cols = list(df.columns)

        chart_type = st.selectbox(
            "Chart type",
            [
                "Bar chart",
                "Histogram",
                "Line chart",
                "Scatter plot",
            ],
        )

        if chart_type == "Bar chart":
            if not all_cols:
                st.info("No columns are available to chart.")

            else:
                col = st.selectbox(
                    "Category or value column",
                    all_cols,
                    key="bar_col",
                )

                top_n = st.slider(
                    "Number of categories to show",
                    min_value=3,
                    max_value=30,
                    value=10,
                )

                counts = (
                    df[col]
                    .astype("object")
                    .where(df[col].notna(), "(Missing)")
                    .value_counts()
                    .head(top_n)
                )

                st.bar_chart(counts)

                st.caption(
                    f"Showing up to {top_n} most frequent values "
                    f"for {col}."
                )

        elif chart_type == "Histogram":
            if not numeric_cols:
                st.info(
                    "A histogram requires at least one numeric column."
                )

            else:
                col = st.selectbox(
                    "Numeric variable",
                    numeric_cols,
                    key="hist_col",
                )

                bins = st.slider(
                    "Number of bins",
                    min_value=5,
                    max_value=50,
                    value=20,
                )

                values = pd.to_numeric(
                    df[col],
                    errors="coerce",
                ).dropna()

                if values.empty:
                    st.warning(
                        "This column has no usable numeric values."
                    )

                else:
                    hist, edges = np.histogram(
                        values,
                        bins=bins,
                    )

                    chart_df = pd.DataFrame(
                        {
                            "Bin range": [
                                f"{edges[i]:.3g}–{edges[i + 1]:.3g}"
                                for i in range(len(hist))
                            ],
                            "Frequency": hist,
                        }
                    ).set_index("Bin range")

                    st.bar_chart(chart_df)

        elif chart_type == "Line chart":
            if not numeric_cols:
                st.info(
                    "A line chart requires at least one numeric column."
                )

            else:
                col = st.selectbox(
                    "Numeric variable",
                    numeric_cols,
                    key="line_col",
                )

                values = pd.to_numeric(
                    df[col],
                    errors="coerce",
                ).reset_index(drop=True)

                st.line_chart(values)

                st.caption(
                    "Points follow the dataset's current row order. "
                    "No time variable is inferred."
                )

        elif chart_type == "Scatter plot":
            if len(numeric_cols) < 2:
                st.info(
                    "A scatter plot requires at least two numeric columns."
                )

            else:
                x_col = st.selectbox(
                    "X-axis variable",
                    numeric_cols,
                    key="scatter_x",
                )

                y_options = [
                    col for col in numeric_cols
                    if col != x_col
                ]

                y_col = st.selectbox(
                    "Y-axis variable",
                    y_options,
                    key="scatter_y",
                )

                plot_df = (
                    df[[x_col, y_col]]
                    .apply(pd.to_numeric, errors="coerce")
                    .dropna()
                )

                if plot_df.empty:
                    st.warning(
                        "The selected variables have no paired "
                        "numeric observations."
                    )

                else:
                    st.scatter_chart(
                        plot_df,
                        x=x_col,
                        y=y_col,
                    )


# ============================================================
# REPORTS AND EXPORTS
# ============================================================

elif page == "Reports & Exports":
    st.title("Reports & Exports")
    st.caption(status_text(MODULES[page][0]))

    df = get_dataset()

    if df is not None:
        st.write(
            "Download the currently loaded dataset and the "
            "descriptive outputs available in this version."
        )

        quota_download_button(
            "Download current dataset as CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_dataset_export.csv",
            mime="text/csv",
            key="download_dataset_reports",
        )

        summary = numeric_summary(df)

        quota_download_button(
            "Download numeric descriptive statistics",
            data=summary.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_descriptive_statistics.csv",
            mime="text/csv",
            key="download_summary_reports",
        )

        quality = variable_quality_profile(df)

        quota_download_button(
            "Download data-quality profile",
            data=quality.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_data_quality.csv",
            mime="text/csv",
            key="download_quality_reports",
        )

        st.info(
            "Automated narrative report generation is under development."
        )

    else:
        st.info(
            "Upload a dataset in Data Management to enable these exports."
        )


# ============================================================
# PROJECT STATUS
# ============================================================

elif page == "Developer Dashboard":
    st.caption("Restricted developer view. Public visitors cannot access this dashboard.")
    render_project_status_dashboard()


# ============================================================
# ABOUT
# ============================================================

elif page == "About":
    st.title(f"About {APP_NAME}")
    st.caption(status_text(MODULES[page][0]))

    st.write(SHORT_DESCRIPTION)
    st.write(APP_DESCRIPTION)
    st.markdown("### Product ownership")
    st.write(f"**TimanStat** is a product of **{APP_ORGANISATION}**. The two names represent separate identities: TimanStat is the software product, while Timan Analytics is the company that owns it.")
    if corporate_logo_path is not None:
        st.image(str(corporate_logo_path), width=230)
        st.caption(f"{APP_ORGANISATION} — parent company")
    st.write(f"**Product tagline:** {APP_TAGLINE}")
    st.write(f"**Version:** {APP_VERSION}")

    st.write(
        "The current prototype supports CSV and Excel import, "
        "worksheet selection, initial data-quality checks, core "
        "descriptive statistics, basic charts and CSV exports. "
        "Additional modules remain under development."
    )

    st.warning(
        "The presence of a module in navigation does not mean its "
        "analytical engine is implemented. Modules marked "
        "Under development are not operational."
    )


# ============================================================
# ACCOUNT & SECURITY
# ============================================================

elif page == "Subscription Administration":
    render_subscription_administration(
        actor_user_id=st.session_state.get("user_id"),
        actor_role=st.session_state.get("role"),
    )


elif page == "User Administration":
    render_user_administration(
        actor_user_id=st.session_state.get("user_id"),
        actor_role=st.session_state.get("role"),
    )


elif page == "Subscription":
    render_subscription_page(
        user_id=st.session_state.get("user_id"),
        organisation_id=st.session_state.get("active_organisation_id"),
    )


elif page == "Account & Security":
    st.title("Account & Security")
    st.caption(status_text(MODULES[page][0]))
    st.write(
        "Manage your sign-in credentials and account protection settings."
    )
    render_password_change()
    st.divider()
    render_contact_methods()
    st.divider()
    render_totp_management()


# ============================================================
# ALL OTHER MODULES
# ============================================================

else:
    show_under_development(
        page,
        MODULES[page][1],
    )