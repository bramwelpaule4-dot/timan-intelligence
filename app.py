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
from timan_intelligence.services.ppswor_report_service import build_ppswor_report
from timan_intelligence.services.analysis_service import (
    run_survey_profile,
    run_survey_weighting_service,
    run_survey_estimation_service,
    run_domain_survey_estimation_service,
    run_weighted_frequency_service,
    run_weighted_numeric_summary_service,
    run_stratified_weighted_mean_service,
    run_stratified_weighted_frequency_service,
    run_cluster_weighted_mean_service,
    run_cluster_weighted_frequency_service,
    run_two_stage_survey_design_inspection_service,
    run_two_stage_survey_total_service,
    run_two_stage_survey_mean_service,
    run_two_stage_survey_proportion_service,
    run_two_stage_survey_domain_total_service,
    run_two_stage_survey_domain_mean_service,
    run_two_stage_survey_domain_proportion_service,
    run_two_stage_ppswr_total_service,
    run_two_stage_ppswr_mean_service,
    run_two_stage_ppswr_proportion_service,
    run_two_stage_ppswor_total_service,
    run_two_stage_ppswor_mean_service,
    run_two_stage_ppswor_proportion_service,
    run_two_stage_ppswor_domain_total_service,
    run_ppswor_total_service,
    run_ppswor_ratio_service,
    run_ppswor_domain_ratio_service,
    run_ppswor_domain_total_service,
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
from timan_intelligence.services.survey_weighting_report import generate_survey_weighting_pdf_report
from timan_intelligence.services.survey_estimation_report import generate_survey_estimation_pdf_report
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
        border-radius: 12px;
        background: rgba(255,255,255,.86);
        box-shadow: 0 2px 8px rgba(23,59,103,.035);
        margin: .45rem 0 .8rem 0;
        overflow: hidden;
    }
    div[data-testid="stExpander"] summary {
        min-height: 3rem;
        padding: .25rem .45rem;
        font-weight: 700;
        color: var(--timan-navy);
    }
    div[data-testid="stExpander"] summary:hover {
        color: var(--timan-blue);
        background: rgba(37,134,199,.045);
    }
    div[data-testid="stExpander"] details[open] > summary {
        border-bottom: 1px solid var(--timan-border);
        background: rgba(37,134,199,.035);
    }
    div[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        padding: .8rem 1rem 1rem 1rem;
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
            padding-top: 1.2rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .sidebar-wordmark { font-size: 22px; }
    }

    /* Statistical workspace hierarchy */
    .analysis-page-header {
        padding: 1.35rem 1.55rem;
        margin: .15rem 0 1rem;
        border: 1px solid var(--timan-border);
        border-left: 5px solid var(--timan-blue);
        border-radius: 13px;
        background: linear-gradient(115deg, #FFFFFF 0%, #F2F7FC 100%);
        box-shadow: 0 5px 18px rgba(23,59,103,.045);
    }
    .analysis-page-eyebrow {
        color: var(--timan-blue);
        font-size: .67rem;
        font-weight: 800;
        letter-spacing: .13em;
        margin-bottom: .45rem;
    }
    .analysis-page-title {
        color: var(--timan-navy);
        font-size: clamp(1.55rem, 2.7vw, 2.05rem);
        font-weight: 850;
        line-height: 1.15;
        letter-spacing: -.035em;
    }
    .analysis-page-description {
        color: var(--timan-muted);
        font-size: .94rem;
        line-height: 1.55;
        margin-top: .45rem;
        max-width: 58rem;
    }
    .analysis-workflow {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .65rem;
        margin: .55rem 0 1rem;
    }
    .analysis-workflow > div {
        display: grid;
        grid-template-columns: 27px 1fr;
        column-gap: .55rem;
        align-items: center;
        padding: .72rem .75rem;
        border: 1px solid var(--timan-border);
        border-radius: 10px;
        background: #FFFFFF;
    }
    .analysis-workflow span {
        grid-row: span 2;
        display: grid;
        place-items: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: rgba(37,134,199,.11);
        color: var(--timan-blue);
        font-size: .78rem;
        font-weight: 800;
    }
    .analysis-workflow strong {
        color: var(--timan-navy);
        font-size: .82rem;
    }
    .analysis-workflow small {
        color: var(--timan-muted);
        font-size: .68rem;
        line-height: 1.3;
    }
    @media (max-width: 760px) {
        .analysis-workflow { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    }
    @media (max-width: 430px) {
        .analysis-workflow { grid-template-columns: 1fr; }
    }

    /* Refined application shell */
    [data-testid="stAppViewContainer"] .main .block-container {
        max-width: 1500px;
    }
    section[data-testid="stSidebar"] {
        box-shadow: 5px 0 24px rgba(16,45,80,.08);
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background: rgba(255,255,255,.045);
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 11px;
        margin: 0 0 9px 0;
        transition: background .18s ease, border-color .18s ease;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"]:hover {
        background: rgba(255,255,255,.075);
        border-color: rgba(117,196,242,.32);
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
        min-height: 2.8rem;
        padding: .45rem .7rem;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
        color: #DCEAF7;
        font-size: .68rem;
        letter-spacing: .10em;
        font-weight: 800;
    }
    section[data-testid="stSidebar"] .stButton > button {
        min-height: 2.45rem;
        margin: 2px 0;
        padding: .48rem .75rem;
        border-radius: 8px;
        font-size: .86rem;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h4 {
        color: #9FCBEA;
        font-size: .68rem;
        font-weight: 800;
        letter-spacing: .13em;
        margin: .25rem 0 .5rem;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        line-height: 1.45;
    }
    div[data-testid="stMetric"] {
        min-height: 112px;
    }
    div[data-testid="stDataFrame"] {
        background: #FFFFFF;
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


def navigate_to(page_name):
    """Navigate to a workspace page using a Streamlit callback."""
    st.session_state.navigation_page = page_name


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

for group_label, group_pages, _default_expanded in navigation_groups:
    available_pages = [
        name for name in group_pages if name in navigation_options
    ]
    if not available_pages:
        continue
    group_is_active = st.session_state.navigation_page in group_pages
    with st.sidebar.expander(group_label, expanded=group_is_active):
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
    df = st.session_state.dataset
    available_modules = sum(
        1 for name, details in MODULES.items()
        if name not in ("Home", "Developer Dashboard")
        and details[0].startswith("Available")
    )
    total_modules = sum(
        1 for name in MODULES
        if name not in ("Home", "Developer Dashboard")
    )

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
            <h1 class="hero-statement">Your analytical workspace</h1>
            <p class="home-description">
                Manage your data, assess its quality and move from descriptive
                exploration towards rigorous statistical analysis and reporting.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-kicker">Workspace overview</div>',
        unsafe_allow_html=True,
    )
    if df is None:
        metric_columns = st.columns(4, gap="medium")
        metric_columns[0].metric("Dataset", "Not loaded")
        metric_columns[1].metric("Records", "—")
        metric_columns[2].metric("Variables", "—")
        metric_columns[3].metric("Available modules", f"{available_modules}/{total_modules}")
        st.info(
            "Your workspace is ready. Upload a CSV or Excel dataset to activate "
            "dataset-specific quality checks, summaries, charts and exports."
        )
        st.button(
            "Upload a dataset",
            type="primary",
            use_container_width=True,
            on_click=go_to_data_management,
        )
    else:
        row_count, column_count = df.shape
        missing_cells = int(df.isna().sum().sum())
        total_cells = row_count * column_count
        completeness = (
            (total_cells - missing_cells) / total_cells * 100
            if total_cells else 100.0
        )
        metric_columns = st.columns(4, gap="medium")
        metric_columns[0].metric("Dataset status", "Loaded")
        metric_columns[1].metric("Records", f"{row_count:,}")
        metric_columns[2].metric("Variables", f"{column_count:,}")
        metric_columns[3].metric("Completeness", f"{completeness:.1f}%")
        st.caption(f"Active dataset: **{st.session_state.dataset_name or 'Uploaded dataset'}**")
        with st.expander("Preview active dataset", expanded=False):
            st.dataframe(df.head(10), use_container_width=True)
            st.caption("Preview limited to the first 10 records.")

    st.markdown(
        '<div class="section-kicker workspace-kicker">Quick access</div>',
        unsafe_allow_html=True,
    )
    quick_access = [
        (
            "Data Management",
            "Upload, replace or inspect your dataset.",
            "Open data workspace",
        ),
        (
            "Data Quality",
            "Review completeness, duplicates and variable structure.",
            "Review data quality",
        ),
        (
            "Descriptive Statistics",
            "Summarise numeric and categorical variables.",
            "Explore statistics",
        ),
        (
            "Survey Analysis",
            "Profile questionnaire data and Likert responses.",
            "Analyse survey data",
        ),
        (
            "Visualisations",
            "Build exploratory charts from available variables.",
            "Create visualisations",
        ),
        (
            "Reports & Exports",
            "Export datasets and available analytical outputs.",
            "View reports",
        ),
    ]
    quick_columns = st.columns(3, gap="medium")
    for index, (target, description, button_label) in enumerate(quick_access):
        with quick_columns[index % 3]:
            st.markdown(
                f"""
                <div class="feature-card {'feature-teal' if index in (1, 3) else 'feature-blue'}">
                    <div class="feature-title">{target}</div>
                    <div class="feature-description">{description}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.button(
                button_label,
                key=f"home_quick_access_{index}",
                use_container_width=True,
                on_click=navigate_to,
                args=(target,),
            )

    st.markdown(
        '<div class="section-kicker workspace-kicker">Platform capabilities</div>',
        unsafe_allow_html=True,
    )
    status_columns = st.columns(3, gap="medium")
    status_columns[0].metric("Available modules", available_modules)
    status_columns[1].metric("In development", total_modules - available_modules)
    status_columns[2].metric("Supported imports", "CSV · XLSX")
    with st.expander("View module availability", expanded=False):
        module_rows = [
            {
                "Module": name,
                "Availability": details[0],
                "Purpose": details[1],
            }
            for name, details in MODULES.items()
            if name not in ("Home", "Developer Dashboard")
        ]
        st.dataframe(
            pd.DataFrame(module_rows),
            hide_index=True,
            use_container_width=True,
        )

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
    st.markdown(
        """
        <section class="analysis-page-header">
            <div class="analysis-page-eyebrow">DATA INTEGRITY · WORKSPACE 02</div>
            <div class="analysis-page-title">Data Quality Assessment</div>
            <div class="analysis-page-description">
                Identify completeness gaps, duplicate records, inconsistent
                fields and potential numeric anomalies before analysis.
                Findings are review flags; source data is never changed automatically.
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.caption(status_text(MODULES[page][0]))
    st.markdown(
        """
        <div class="analysis-workflow">
            <div><strong>01</strong><b>Inspect</b><small>Dataset structure</small></div>
            <div><strong>02</strong><b>Measure</b><small>Quality indicators</small></div>
            <div><strong>03</strong><b>Review</b><small>Flagged records</small></div>
            <div><strong>04</strong><b>Improve</b><small>Plan corrections</small></div>
        </div>
        """,
        unsafe_allow_html=True,
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

        st.markdown("#### Dataset quality snapshot")
        st.caption(
            f"Active dataset · {row_count:,} records · {column_count:,} variables"
        )
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
    st.markdown(
        """
        <section class="analysis-page-header">
            <div class="analysis-page-eyebrow">SURVEY INTELLIGENCE · WORKSPACE 03</div>
            <div class="analysis-page-title">Survey Analysis</div>
            <div class="analysis-page-description">
                Explore respondent records, question structures, response
                distributions, multiple-response items, Likert scales and
                documented survey weights.
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.caption(status_text(MODULES[page][0]))
    st.markdown(
        """
        <div class="analysis-workflow">
            <div><strong>01</strong><b>Profile</b><small>Recognise structure</small></div>
            <div><strong>02</strong><b>Explore</b><small>Inspect responses</small></div>
            <div><strong>03</strong><b>Analyse</b><small>Estimate patterns</small></div>
            <div><strong>04</strong><b>Interpret</b><small>Check limitations</small></div>
        </div>
        """,
        unsafe_allow_html=True,
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

        st.markdown("#### Survey structure snapshot")
        st.caption(
            f"Active dataset · {len(df):,} imported records · "
            f"{len(df.columns):,} source variables"
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
            "fractions and design-based totals, means and proportions with Taylor-linearised standard errors. You can flag certainty (take-all) PSUs for correct first-stage variance handling."
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
            ms_certainty_options = [
                x for x in ms_cols
                if x not in (
                    ms_weight, ms_psu, ms_ssu, ms_strata,
                    ms_psu_population, ms_ssu_population,
                )
            ]
            ms_use_certainty = st.checkbox(
                "The sample includes certainty (take-all) PSUs",
                value=False, key="multistage_use_certainty_psus",
            )
            ms_certainty_psu = None
            if ms_use_certainty:
                if ms_certainty_options:
                    ms_certainty_psu = st.selectbox(
                        "PSU certainty indicator (true/false or yes/no)",
                        ms_certainty_options,
                        key="multistage_certainty_psu_variable",
                    )
                else:
                    st.info("Add a variable identifying certainty PSUs.")
            ms_design_key = (
                _dataset_analysis_key(df), ms_weight, ms_psu, ms_ssu,
                ms_strata, ms_psu_population, ms_ssu_population, ms_certainty_psu,
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
                        ms_psu, ms_ssu, ms_certainty_psu,
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
                        ms_confidence, ms_certainty_psu,
                    )
                    if st.button(
                        "Estimate two-stage population total",
                        type="primary", key="run_two_stage_total",
                    ):
                        try:
                            total_result = run_two_stage_survey_total_service(
                                df, ms_outcome, ms_psu, ms_ssu,
                                ms_psu_population, ms_ssu_population,
                                ms_strata, ms_confidence, ms_certainty_psu,
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

                    st.divider()
                    st.subheader("Two-stage population mean")
                    st.write(
                        "Estimate the mean per eligible population element. Supply an "
                        "SSU-level outcome total and the number of eligible elements "
                        "enumerated in each sampled SSU."
                    )
                    ratio_denominator_options = [
                        x for x in ms_numeric
                        if x not in (
                            ms_weight, ms_psu_population, ms_ssu_population,
                            ms_psu, ms_ssu, ms_strata, ms_outcome, ms_certainty_psu,
                        )
                    ]
                    if ratio_denominator_options:
                        mean_denominator = st.selectbox(
                            "Eligible element count in each SSU",
                            ratio_denominator_options,
                            key="multistage_mean_denominator",
                        )
                        mean_key = (
                            _dataset_analysis_key(df), ms_outcome, mean_denominator,
                            ms_psu, ms_ssu, ms_strata, ms_psu_population,
                            ms_ssu_population, ms_confidence, ms_certainty_psu,
                        )
                        if st.button(
                            "Estimate two-stage population mean",
                            key="run_two_stage_mean",
                        ):
                            try:
                                mean_result = run_two_stage_survey_mean_service(
                                    df, ms_outcome, mean_denominator, ms_psu, ms_ssu,
                                    ms_psu_population, ms_ssu_population,
                                    ms_strata, ms_confidence, ms_certainty_psu,
                                )
                                st.session_state["two_stage_mean_result"] = mean_result
                                st.session_state["two_stage_mean_result_key"] = mean_key
                            except (TypeError, ValueError, KeyError) as exc:
                                st.error(str(exc))
                        saved_mean = st.session_state.get("two_stage_mean_result")
                        if (
                            saved_mean is not None
                            and st.session_state.get("two_stage_mean_result_key") == mean_key
                        ):
                            st.metric("Estimated population mean", f"{saved_mean.metadata['estimate']:,.4g}")
                            st.metric("Design-based standard error", f"{saved_mean.metadata['standard_error']:,.4g}")
                            ci = saved_mean.metadata["confidence_interval"]
                            st.write(f"{ms_confidence:.0%} confidence interval: [{ci[0]:,.4g}, {ci[1]:,.4g}]")
                            st.dataframe(saved_mean.tables["stratum_estimates"], hide_index=True, use_container_width=True)
                            for warning in saved_mean.limitations:
                                st.warning(warning)
                    else:
                        st.info("Add a numeric eligible-element count for each sampled SSU to estimate a population mean.")

                    st.divider()
                    st.subheader("Two-stage population proportion")
                    st.write(
                        "Estimate a proportion from the number of successes and "
                        "eligible elements enumerated in each sampled SSU. The "
                        "success count cannot exceed the eligible count."
                    )
                    if ratio_denominator_options:
                        proportion_successes = st.selectbox(
                            "Number of successes in each SSU",
                            outcome_options,
                            key="multistage_proportion_successes",
                        )
                        proportion_denominator_options = [
                            x for x in ratio_denominator_options
                            if x != proportion_successes
                        ]
                        if proportion_denominator_options:
                            proportion_denominator = st.selectbox(
                                "Eligible population count in each SSU",
                                proportion_denominator_options,
                                key="multistage_proportion_denominator",
                            )
                            proportion_key = (
                                _dataset_analysis_key(df), proportion_successes,
                                proportion_denominator, ms_psu, ms_ssu, ms_strata,
                                ms_psu_population, ms_ssu_population, ms_confidence,
                                ms_certainty_psu,
                            )
                            if st.button(
                                "Estimate two-stage population proportion",
                                key="run_two_stage_proportion",
                            ):
                                try:
                                    proportion_result = run_two_stage_survey_proportion_service(
                                        df, proportion_successes, proportion_denominator,
                                        ms_psu, ms_ssu, ms_psu_population,
                                        ms_ssu_population, ms_strata, ms_confidence,
                                        ms_certainty_psu,
                                    )
                                    st.session_state["two_stage_proportion_result"] = proportion_result
                                    st.session_state["two_stage_proportion_result_key"] = proportion_key
                                except (TypeError, ValueError, KeyError) as exc:
                                    st.error(str(exc))
                            saved_proportion = st.session_state.get("two_stage_proportion_result")
                            if (
                                saved_proportion is not None
                                and st.session_state.get("two_stage_proportion_result_key") == proportion_key
                            ):
                                st.metric("Estimated population proportion", f"{saved_proportion.metadata['estimate']:.2%}")
                                st.metric("Design-based standard error", f"{saved_proportion.metadata['standard_error']:.4f}")
                                ci = saved_proportion.metadata["confidence_interval"]
                                st.write(f"{ms_confidence:.0%} confidence interval: [{ci[0]:.2%}, {ci[1]:.2%}]")
                                st.dataframe(saved_proportion.tables["stratum_estimates"], hide_index=True, use_container_width=True)
                                for warning in saved_proportion.limitations:
                                    st.warning(warning)
                        else:
                            st.info("Select a separate numeric eligible-element count variable.")
                    else:
                        st.info("Add a numeric eligible-element count for each sampled SSU to estimate a population proportion.")
                else:
                    st.info("No eligible numeric SSU outcome variable is available.")

        st.divider()
        st.subheader("Two-stage survey domain estimation")
        st.write(
            "Estimate totals, means or proportions for an SSU-level subpopulation. "
            "The estimator retains every sampled SSU—including those outside the "
            "selected domain—when calculating design-based variance."
        )
        st.caption(
            "Domain membership must be constant within each SSU in this version. "
            "For person-level subgroups within mixed households or clusters, first "
            "prepare SSU-level domain-specific outcome and eligible-count totals."
        )
        domain_excluded = {
            ms_weight, ms_psu, ms_ssu, ms_strata,
            ms_psu_population, ms_ssu_population, ms_certainty_psu,
        }
        domain_variable_options = [x for x in ms_cols if x not in domain_excluded]
        if ms_psu_population is not None and ms_ssu_population is not None and domain_variable_options:
            domain_variable = st.selectbox(
                "Domain classification variable", domain_variable_options,
                key="multistage_domain_variable",
            )
            domain_values = df[domain_variable].dropna().unique().tolist()
            if domain_values:
                domain_value = st.selectbox(
                    "Subpopulation to estimate", domain_values,
                    format_func=str, key="multistage_domain_value",
                )
                domain_kind = st.selectbox(
                    "Domain parameter", ["Total", "Mean", "Proportion"],
                    key="multistage_domain_kind",
                )
                domain_outcome_options = [
                    x for x in ms_numeric
                    if x not in domain_excluded and x != domain_variable
                ]
                if domain_outcome_options:
                    domain_outcome = st.selectbox(
                        "Domain outcome / numerator total", domain_outcome_options,
                        key="multistage_domain_outcome",
                    )
                    domain_denominator_options = [
                        x for x in domain_outcome_options if x != domain_outcome
                    ]
                    domain_denominator = None
                    if domain_kind in ("Mean", "Proportion") and domain_denominator_options:
                        domain_denominator = st.selectbox(
                            "Domain eligible-element count", domain_denominator_options,
                            key="multistage_domain_denominator",
                        )
                    elif domain_kind in ("Mean", "Proportion"):
                        st.info("A separate numeric eligible-element count is required.")
                    domain_key = (
                        _dataset_analysis_key(df), domain_kind, domain_variable,
                        str(domain_value), domain_outcome, domain_denominator,
                        ms_psu, ms_ssu, ms_strata, ms_psu_population,
                        ms_ssu_population, ms_confidence, ms_certainty_psu,
                    )
                    can_run_domain = domain_kind == "Total" or domain_denominator is not None
                    if can_run_domain and st.button(
                        f"Estimate two-stage domain {domain_kind.lower()}",
                        type="primary", key="run_two_stage_domain",
                    ):
                        try:
                            common_domain_args = (
                                df, domain_outcome, domain_variable, domain_value,
                                ms_psu, ms_ssu, ms_psu_population,
                                ms_ssu_population, ms_strata, ms_confidence,
                                ms_certainty_psu,
                            )
                            if domain_kind == "Total":
                                domain_result = run_two_stage_survey_domain_total_service(
                                    *common_domain_args
                                )
                            elif domain_kind == "Mean":
                                domain_result = run_two_stage_survey_domain_mean_service(
                                    df, domain_outcome, domain_denominator,
                                    domain_variable, domain_value, ms_psu, ms_ssu,
                                    ms_psu_population, ms_ssu_population,
                                    ms_strata, ms_confidence, ms_certainty_psu,
                                )
                            else:
                                domain_result = run_two_stage_survey_domain_proportion_service(
                                    df, domain_outcome, domain_denominator,
                                    domain_variable, domain_value, ms_psu, ms_ssu,
                                    ms_psu_population, ms_ssu_population,
                                    ms_strata, ms_confidence, ms_certainty_psu,
                                )
                            st.session_state["two_stage_domain_result"] = domain_result
                            st.session_state["two_stage_domain_result_key"] = domain_key
                        except (TypeError, ValueError, KeyError) as exc:
                            st.error(str(exc))
                    saved_domain = st.session_state.get("two_stage_domain_result")
                    if (
                        saved_domain is not None
                        and st.session_state.get("two_stage_domain_result_key") == domain_key
                    ):
                        domain_estimate = saved_domain.metadata["estimate"]
                        st.metric(
                            f"Estimated domain {domain_kind.lower()}",
                            f"{domain_estimate:.2%}" if domain_kind == "Proportion"
                            else f"{domain_estimate:,.4g}",
                        )
                        st.metric(
                            "Design-based standard error",
                            f"{saved_domain.metadata['standard_error']:.4g}",
                        )
                        domain_ci = saved_domain.metadata["confidence_interval"]
                        if domain_kind == "Proportion":
                            st.write(
                                f"{ms_confidence:.0%} confidence interval: "
                                f"[{domain_ci[0]:.2%}, {domain_ci[1]:.2%}]"
                            )
                        else:
                            st.write(
                                f"{ms_confidence:.0%} confidence interval: "
                                f"[{domain_ci[0]:,.4g}, {domain_ci[1]:,.4g}]"
                            )
                        st.dataframe(
                            saved_domain.tables["stratum_estimates"],
                            hide_index=True, use_container_width=True,
                        )
                        with st.expander("Domain PSU-level design details"):
                            st.dataframe(
                                saved_domain.tables["psu_details"],
                                hide_index=True, use_container_width=True,
                            )
                        for warning in saved_domain.limitations:
                            st.warning(warning)
            else:
                st.info("The selected domain variable has no observed non-missing values.")
        else:
            st.info(
                "Domain estimation requires both stage population counts and "
                "a domain classification variable."
            )

        with st.expander("Two-stage PPS with replacement (PPSWR) estimation"):
            st.write(
                "Use this separate estimator when PSUs were independently selected "
                "with replacement using known per-draw selection probabilities, "
                "followed by SRSWOR of SSUs within each selected PSU draw. A unique "
                "draw ID is essential when a physical PSU is selected more than once."
            )
            st.warning(
                "Do not use this option for PPS without replacement, systematic PPS, "
                "or when selection probabilities are guessed from PSU size measures. "
                "Supply probabilities from the actual first-stage sampling design."
            )
            pps_identifier_options = [x for x in ms_cols if x not in (ms_ssu,)]
            pps_psu = st.selectbox(
                "Physical PSU identifier", pps_identifier_options,
                key="ppswr_psu_variable",
            )
            pps_draw_options = [x for x in ms_cols if x not in (pps_psu, ms_ssu)]
            pps_draw = st.selectbox(
                "Unique PSU draw identifier", pps_draw_options,
                key="ppswr_draw_variable",
            )
            pps_ssu = st.selectbox(
                "SSU identifier", [x for x in ms_cols if x not in (pps_psu, pps_draw)],
                key="ppswr_ssu_variable",
            )
            pps_probability_options = [
                x for x in ms_numeric
                if x not in (pps_psu, pps_draw, pps_ssu, ms_strata)
            ]
            pps_probability = st.selectbox(
                "Per-draw PSU selection probability", pps_probability_options,
                key="ppswr_probability_variable",
            )
            pps_ssu_population_options = [
                x for x in pps_probability_options if x != pps_probability
            ]
            pps_ssu_population = st.selectbox(
                "Population SSU count in each selected PSU", pps_ssu_population_options,
                key="ppswr_ssu_population_variable",
            )
            pps_outcome_options = [
                x for x in pps_ssu_population_options if x != pps_ssu_population
            ]
            pps_kind = st.selectbox(
                "PPSWR parameter", ["Total", "Mean", "Proportion"],
                key="ppswr_parameter_kind",
            )
            pps_outcome = st.selectbox(
                "SSU outcome / numerator total", pps_outcome_options,
                key="ppswr_outcome_variable",
            )
            pps_denominator_options = [
                x for x in pps_outcome_options if x != pps_outcome
            ]
            pps_denominator = None
            if pps_kind in ("Mean", "Proportion") and pps_denominator_options:
                pps_denominator = st.selectbox(
                    "SSU eligible-element count", pps_denominator_options,
                    key="ppswr_denominator_variable",
                )
            pps_confidence = st.selectbox(
                "PPSWR confidence level", [0.90, 0.95, 0.99],
                index=1, format_func=lambda x: f"{x:.0%}",
                key="ppswr_confidence_level",
            )
            pps_key = (
                _dataset_analysis_key(df), pps_kind, pps_psu, pps_draw, pps_ssu,
                pps_probability, pps_ssu_population, pps_outcome,
                pps_denominator, ms_strata, pps_confidence,
            )
            pps_ready = (
                all(value is not None for value in (
                    pps_psu, pps_draw, pps_ssu, pps_probability,
                    pps_ssu_population, pps_outcome,
                ))
                and pps_psu != pps_draw and pps_psu != pps_ssu
                and pps_draw != pps_ssu and pps_outcome not in (
                    pps_psu, pps_draw, pps_ssu, pps_probability, pps_ssu_population,
                )
                and (pps_kind == "Total" or pps_denominator is not None)
            )
            if st.button(
                "Run two-stage PPSWR estimate",
                type="primary", key="run_two_stage_ppswr",
                disabled=not pps_ready,
            ):
                try:
                    common_pps_args = (
                        df, pps_outcome, pps_psu, pps_draw, pps_ssu,
                        pps_ssu_population, pps_probability, ms_strata, pps_confidence,
                    )
                    if pps_kind == "Total":
                        pps_result = run_two_stage_ppswr_total_service(
                            df, pps_outcome, pps_psu, pps_draw, pps_ssu,
                            pps_ssu_population, pps_probability, ms_strata, pps_confidence,
                        )
                    elif pps_kind == "Mean":
                        pps_result = run_two_stage_ppswr_mean_service(
                            df, pps_outcome, pps_denominator, pps_psu, pps_draw,
                            pps_ssu, pps_ssu_population, pps_probability,
                            ms_strata, pps_confidence,
                        )
                    else:
                        pps_result = run_two_stage_ppswr_proportion_service(
                            df, pps_outcome, pps_denominator, pps_psu, pps_draw,
                            pps_ssu, pps_ssu_population, pps_probability,
                            ms_strata, pps_confidence,
                        )
                    st.session_state["two_stage_ppswr_result"] = pps_result
                    st.session_state["two_stage_ppswr_result_key"] = pps_key
                except (TypeError, ValueError, KeyError) as exc:
                    st.error(str(exc))
            saved_pps = st.session_state.get("two_stage_ppswr_result")
            if (
                saved_pps is not None
                and st.session_state.get("two_stage_ppswr_result_key") == pps_key
            ):
                estimate = saved_pps.metadata["estimate"]
                st.metric(
                    f"Estimated population {pps_kind.lower()}",
                    f"{estimate:.2%}" if pps_kind == "Proportion" else f"{estimate:,.4g}",
                )
                st.metric(
                    "Design-based standard error",
                    f"{saved_pps.metadata['standard_error']:.4g}",
                )
                ci = saved_pps.metadata["confidence_interval"]
                if pps_kind == "Proportion":
                    st.write(f"{pps_confidence:.0%} confidence interval: [{ci[0]:.2%}, {ci[1]:.2%}]")
                else:
                    st.write(f"{pps_confidence:.0%} confidence interval: [{ci[0]:,.4g}, {ci[1]:,.4g}]")
                st.dataframe(saved_pps.tables["stratum_estimates"], hide_index=True, use_container_width=True)
                if "psu_draw_details" in saved_pps.tables:
                    with st.expander("PSU draw-level details"):
                        st.dataframe(saved_pps.tables["psu_draw_details"], hide_index=True, use_container_width=True)
                for warning in saved_pps.limitations:
                    st.warning(warning)

        with st.expander("Two-stage PPS without replacement (PPSWOR) estimation"):
            st.write(
                "Estimate population totals, means, binary proportions or domain totals "
                "when PSUs were selected by fixed-size PPS without replacement and SSUs "
                "were selected by SRSWOR within sampled PSUs. Supply one row per sampled SSU."
            )
            st.warning(
                "For stratified designs, upload one joint-inclusion matrix worksheet per stratum. "
                "Use actual first-order PSU inclusion probabilities and the complete "
                "symmetric second-order joint inclusion matrix (pi_ij) from the design. "
                "Do not substitute normalized weights, size measures or conditional draw "
                "probabilities. Respondent subsampling within SSUs is not supported."
            )
            two_pps_design = st.radio(
                "First-stage PPSWOR design structure",
                ["Unstratified", "Stratified"],
                horizontal=True, key="two_ppswor_design_structure",
            )
            two_pps_kind = st.selectbox(
                "PPSWOR estimand",
                ["Total", "Mean", "Proportion", "Domain total"],
                key="two_ppswor_estimand_kind",
            )
            two_pps_psu = st.selectbox(
                "PSU identifier", ms_cols, key="two_ppswor_psu_variable"
            )
            two_pps_ssu_options = [x for x in ms_cols if x != two_pps_psu]
            two_pps_ssu = st.selectbox(
                "SSU identifier", two_pps_ssu_options,
                key="two_ppswor_ssu_variable",
            )
            two_pps_structural = {two_pps_psu, two_pps_ssu}
            two_pps_strata = None
            if two_pps_design == "Stratified":
                two_pps_strata_options = [
                    x for x in ms_cols if x not in (two_pps_psu, two_pps_ssu)
                ]
                two_pps_strata = st.selectbox(
                    "Stratum identifier", two_pps_strata_options,
                    key="two_ppswor_strata_variable",
                )
            two_pps_structural = {two_pps_psu, two_pps_ssu, two_pps_strata}
            two_pps_numeric = [
                x for x in ms_numeric if x not in two_pps_structural
            ]
            two_pps_pi = st.selectbox(
                "First-order PSU inclusion probability (pi_i)", two_pps_numeric,
                key="two_ppswor_pi_variable",
            )
            two_pps_population_options = [
                x for x in two_pps_numeric if x != two_pps_pi
            ]
            two_pps_population = st.selectbox(
                "Population SSU count in each PSU (M_i)", two_pps_population_options,
                key="two_ppswor_population_variable",
            )
            two_pps_outcome_options = [
                x for x in two_pps_population_options if x != two_pps_population
            ]
            two_pps_outcome = st.selectbox(
                "SSU outcome variable", two_pps_outcome_options,
                key="two_ppswor_outcome_variable",
            )
            two_pps_denominator = None
            two_pps_domain_variable = None
            two_pps_domain_value = None
            if two_pps_kind in ("Mean", "Proportion"):
                two_pps_denominator = st.number_input(
                    "Known total number of SSUs in the target population",
                    min_value=1, value=1, step=1,
                    key="two_ppswor_population_denominator",
                    help=(
                        "This is a fixed, known population SSU count—not an estimated "
                        "denominator or a sum of sample weights."
                    ),
                )
                st.caption(
                    "The mean/proportion estimator divides the design-based total by "
                    "this known population SSU count. Proportion inputs must be coded 0/1."
                )
            elif two_pps_kind == "Domain total":
                two_pps_domain_options = [
                    x for x in ms_cols
                    if x not in two_pps_structural
                    and x not in (two_pps_pi, two_pps_population, two_pps_outcome)
                ]
                if two_pps_domain_options:
                    two_pps_domain_variable = st.selectbox(
                        "Domain / subgroup variable", two_pps_domain_options,
                        key="two_ppswor_domain_variable",
                    )
                    two_pps_domain_values = [
                        value for value in df[two_pps_domain_variable].dropna().unique().tolist()
                    ]
                    if two_pps_domain_values:
                        two_pps_domain_value = st.selectbox(
                            "Domain value", two_pps_domain_values,
                            key="two_ppswor_domain_value",
                            format_func=lambda value: str(value),
                        )
                    else:
                        st.warning("The selected domain variable has no non-missing values.")
                else:
                    st.warning("No eligible domain variable is available in this dataset.")
            two_pps_confidence = st.selectbox(
                "Two-stage PPSWOR confidence level", [0.90, 0.95, 0.99],
                index=1, format_func=lambda x: f"{x:.0%}",
                key="two_ppswor_confidence_level",
            )
            if two_pps_design == "Stratified":
                st.info(
                    "Upload one Excel workbook (.xlsx) with one worksheet per stratum. "
                    "Each worksheet name must exactly match its stratum label. The first "
                    "column and column headers identify the same PSUs in that stratum."
                )
                two_pps_matrix_file = st.file_uploader(
                    "Stratum-specific joint inclusion matrices (.xlsx)",
                    type=["xlsx"], key="two_ppswor_stratified_matrix_upload",
                )
                two_pps_joint_text = ""
            else:
                st.caption(
                    "Paste a square CSV matrix: the first column contains PSU IDs, "
                    "the header row contains the same PSU IDs, and each cell contains "
                    "the actual joint inclusion probability pi_ij. Diagonal cells must "
                    "equal pi_i."
                )
                two_pps_joint_text = st.text_area(
                    "Second-order PSU joint inclusion probability matrix (CSV)",
                    placeholder=(
                        ",P1,P2,P3\\n"
                        "P1,0.50,0.20,0.30\\n"
                        "P2,0.20,0.70,0.50\\n"
                        "P3,0.30,0.50,0.80"
                    ),
                    height=150,
                    key="two_ppswor_joint_matrix_csv",
                )
                two_pps_matrix_file = None
            two_pps_key = (
                _dataset_analysis_key(df), two_pps_kind, two_pps_psu, two_pps_ssu,
                two_pps_pi, two_pps_population, two_pps_outcome,
                two_pps_denominator, two_pps_domain_variable, two_pps_domain_value,
                two_pps_confidence, two_pps_joint_text, two_pps_design,
                two_pps_strata,
                hashlib.sha256(two_pps_matrix_file.getvalue()).hexdigest()
                if two_pps_matrix_file is not None else None,
            )
            two_pps_required = [
                two_pps_psu, two_pps_ssu, two_pps_pi,
                two_pps_population, two_pps_outcome,
            ]
            two_pps_ready = (
                all(value is not None for value in two_pps_required)
                and len(set(two_pps_required)) == 5
                and (
                    (two_pps_design == "Unstratified" and bool(two_pps_joint_text.strip()))
                    or (two_pps_design == "Stratified" and two_pps_matrix_file is not None
                        and two_pps_strata is not None)
                )
                and (
                    two_pps_kind not in ("Mean", "Proportion")
                    or two_pps_denominator is not None
                )
                and (
                    two_pps_kind != "Domain total"
                    or (
                        two_pps_domain_variable is not None
                        and two_pps_domain_value is not None
                    )
                )
            )
            if st.button(
                f"Run two-stage PPSWOR {two_pps_kind.lower()} estimate",
                type="primary", key="run_two_stage_ppswor",
                disabled=not two_pps_ready,
            ):
                try:
                    if two_pps_design == "Stratified":
                        matrix_bytes = two_pps_matrix_file.getvalue()
                        workbook = pd.ExcelFile(io.BytesIO(matrix_bytes))
                        observed_strata = df[two_pps_strata].dropna().unique().tolist()
                        expected_sheets = {str(value): value for value in observed_strata}
                        if len(expected_sheets) != len(observed_strata):
                            raise ValueError(
                                "Stratum labels must have unique text representations "
                                "to map them safely to Excel worksheet names."
                            )
                        missing_sheets = sorted(set(expected_sheets) - set(workbook.sheet_names))
                        extra_sheets = sorted(set(workbook.sheet_names) - set(expected_sheets))
                        if missing_sheets or extra_sheets:
                            raise ValueError(
                                "Workbook worksheets must match observed strata exactly. "
                                f"Missing: {missing_sheets or 'none'}; "
                                f"unexpected: {extra_sheets or 'none'}."
                            )
                        joint_matrix = {}
                        for sheet_name, stratum_value in expected_sheets.items():
                            matrix = pd.read_excel(
                                workbook, sheet_name=sheet_name, index_col=0
                            )
                            if matrix.empty or not matrix.index.is_unique or not matrix.columns.is_unique:
                                raise ValueError(
                                    f"Worksheet {sheet_name!r} must be a non-empty matrix "
                                    "with unique PSU row and column labels."
                                )
                            stratum_ids = (
                                df.loc[df[two_pps_strata] == stratum_value, two_pps_psu]
                                .dropna().tolist()
                            )
                            label_lookup = {str(value): value for value in stratum_ids}
                            matrix.index = [label_lookup.get(str(value), value) for value in matrix.index]
                            matrix.columns = [label_lookup.get(str(value), value) for value in matrix.columns]
                            if set(matrix.index) != set(matrix.columns):
                                raise ValueError(
                                    f"Worksheet {sheet_name!r} row and column PSU labels must match."
                                )
                            ordered_ids = list(dict.fromkeys(stratum_ids))
                            joint_matrix[stratum_value] = matrix.loc[ordered_ids, ordered_ids]
                    else:
                        joint_matrix = pd.read_csv(
                            io.StringIO(two_pps_joint_text.strip()), index_col=0
                        )
                        joint_matrix.index = joint_matrix.index.map(str)
                        joint_matrix.columns = joint_matrix.columns.map(str)
                    if two_pps_kind == "Total":
                        two_pps_result = run_two_stage_ppswor_total_service(
                            df, two_pps_outcome, two_pps_psu, two_pps_ssu,
                            two_pps_pi, two_pps_population, joint_matrix,
                            two_pps_strata, two_pps_confidence,
                        )
                    elif two_pps_kind == "Mean":
                        two_pps_result = run_two_stage_ppswor_mean_service(
                            df, two_pps_outcome, two_pps_denominator,
                            two_pps_psu, two_pps_ssu, two_pps_pi,
                            two_pps_population, joint_matrix, two_pps_strata,
                            two_pps_confidence,
                        )
                    elif two_pps_kind == "Proportion":
                        two_pps_result = run_two_stage_ppswor_proportion_service(
                            df, two_pps_outcome, two_pps_denominator,
                            two_pps_psu, two_pps_ssu, two_pps_pi,
                            two_pps_population, joint_matrix, two_pps_strata,
                            two_pps_confidence,
                        )
                    else:
                        two_pps_result = run_two_stage_ppswor_domain_total_service(
                            df, two_pps_outcome, two_pps_domain_variable,
                            two_pps_domain_value, two_pps_psu, two_pps_ssu,
                            two_pps_pi, two_pps_population, joint_matrix, two_pps_strata,
                            two_pps_confidence,
                        )
                    st.session_state["two_stage_ppswor_result"] = two_pps_result
                    st.session_state["two_stage_ppswor_result_key"] = two_pps_key
                except (TypeError, ValueError, KeyError, pd.errors.ParserError, ImportError) as exc:
                    st.error(str(exc))
            saved_two_pps = st.session_state.get("two_stage_ppswor_result")
            if (
                saved_two_pps is not None
                and st.session_state.get("two_stage_ppswor_result_key") == two_pps_key
            ):
                meta = saved_two_pps.metadata
                estimate_label = (
                    f"Estimated population {two_pps_kind.lower()}"
                    if two_pps_kind != "Domain total"
                    else f"Estimated total for {two_pps_domain_variable} = {two_pps_domain_value}"
                )
                metric_left, metric_right, metric_variance = st.columns(3)
                estimate_display = (
                    f"{meta['estimate']:.2%}"
                    if two_pps_kind == "Proportion"
                    else f"{meta['estimate']:,.4g}"
                )
                metric_left.metric(estimate_label, estimate_display)
                metric_right.metric(
                    "Design-based standard error", f"{meta['standard_error']:,.4g}"
                )
                metric_variance.metric("Combined variance", f"{meta['variance']:,.4g}")
                ci = meta["confidence_interval"]
                if two_pps_kind == "Proportion":
                    st.write(
                        f"{meta['confidence_level']:.0%} confidence interval: "
                        f"[{ci[0]:.2%}, {ci[1]:.2%}]"
                    )
                else:
                    st.write(
                        f"{meta['confidence_level']:.0%} confidence interval: "
                        f"[{ci[0]:,.4g}, {ci[1]:,.4g}]"
                    )
                st.caption(
                    f"Stage 1 variance: {meta['stage_1_variance']:,.4g} · "
                    f"Stage 2 variance: {meta['stage_2_variance']:,.4g}"
                )
                for finding in saved_two_pps.findings:
                    st.write(f"• {finding}")
                st.dataframe(
                    saved_two_pps.tables["stratum_estimates"],
                    hide_index=True, use_container_width=True,
                )
                with st.expander("Sampled PSU and SSU details"):
                    st.dataframe(
                        saved_two_pps.tables["psu_details"],
                        hide_index=True, use_container_width=True,
                    )
                with st.expander("First-stage pairwise variance details"):
                    st.dataframe(
                        saved_two_pps.tables["pairwise_variance"],
                        hide_index=True, use_container_width=True,
                    )
                for warning in saved_two_pps.limitations:
                    st.warning(warning)

        with st.expander("PSU-level PPS without replacement (PPSWOR) estimation"):
            st.write(
                "Use this estimator when PSUs were selected by a fixed-size "
                "PPS-without-replacement design and each sampled PSU has a fully "
                "observed outcome total. It uses the Horvitz–Thompson estimator "
                "with Sen–Yates–Grundy (SYG) variance."
            )
            st.warning(
                "This PSU-level option requires fully observed PSU totals and "
                "does not support SSU subsampling. For PPSWOR of PSUs followed by "
                "SRSWOR of SSUs, use the separate two-stage PPSWOR estimator above. "
                "Mean, proportion and domain ratio estimators are provided separately. "
                "Supply actual design inclusion probabilities; do not derive them "
                "from size measures or normalized weights."
            )
            ppswor_psu = st.selectbox(
                "Sampled PSU identifier", ms_cols, key="ppswor_psu_variable"
            )
            ppswor_numeric = [
                x for x in ms_numeric if x not in (ppswor_psu, ms_strata)
            ]
            ppswor_outcome = st.selectbox(
                "Fully observed PSU outcome total", ppswor_numeric,
                key="ppswor_outcome_variable",
            )
            ppswor_pi_options = [
                x for x in ppswor_numeric if x != ppswor_outcome
            ]
            ppswor_pi = st.selectbox(
                "First-order inclusion probability (pi_i)", ppswor_pi_options,
                key="ppswor_pi_variable",
            )
            ppswor_stratification = st.radio(
                "PPSWOR design structure",
                ["Unstratified", "Stratified"],
                horizontal=True, key="ppswor_stratification",
            )
            ppswor_strata = None
            ppswor_strata_options = [
                x for x in ms_cols
                if x not in (ppswor_psu, ppswor_outcome, ppswor_pi)
            ]
            if ppswor_stratification == "Stratified":
                ppswor_strata = st.selectbox(
                    "Stratum identifier", ppswor_strata_options,
                    key="ppswor_strata_variable",
                )
                st.info(
                    "Upload one Excel workbook (.xlsx) with one worksheet per "
                    "stratum. Each worksheet name must exactly match its stratum "
                    "label and contain that stratum's square pi_ij matrix. The "
                    "first column is PSU IDs; column headers are the same PSU IDs."
                )
                ppswor_matrix_file = st.file_uploader(
                    "Upload stratum-specific joint inclusion matrices (.xlsx)",
                    type=["xlsx"], key="ppswor_stratified_matrix_upload",
                )
            else:
                ppswor_matrix_file = st.file_uploader(
                    "Upload joint inclusion probability matrix (CSV)",
                    type=["csv"], key="ppswor_joint_matrix_upload",
                    help=(
                        "Square CSV matrix: first column contains PSU identifiers; "
                        "column headers contain the same PSU identifiers; each cell "
                        "is the design joint inclusion probability pi_ij."
                    ),
                )
            ppswor_confidence = st.selectbox(
                "PPSWOR confidence level", [0.90, 0.95, 0.99],
                index=1, format_func=lambda x: f"{x:.0%}",
                key="ppswor_confidence_level",
            )
            ppswor_ready = (
                ppswor_psu is not None
                and ppswor_outcome is not None
                and ppswor_pi is not None
                and len({ppswor_psu, ppswor_outcome, ppswor_pi}) == 3
                and (
                    ppswor_stratification == "Unstratified"
                    or (
                        ppswor_strata is not None
                        and ppswor_strata not in (
                            ppswor_psu, ppswor_outcome, ppswor_pi
                        )
                    )
                )
                and ppswor_matrix_file is not None
            )
            if st.button(
                "Run PSU-level PPSWOR total",
                type="primary", key="run_ppswor_total",
                disabled=not ppswor_ready,
            ):
                try:
                    matrix_bytes = ppswor_matrix_file.getvalue()
                    matrix_digest = hashlib.sha256(matrix_bytes).hexdigest()
                    if ppswor_stratification == "Stratified":
                        workbook = pd.ExcelFile(io.BytesIO(matrix_bytes))
                        observed_strata = df[ppswor_strata].dropna().unique().tolist()
                        expected_sheets = {str(value): value for value in observed_strata}
                        if len(expected_sheets) != len(observed_strata):
                            raise ValueError(
                                "Stratum labels must have unique text representations "
                                "to map them safely to Excel worksheet names."
                            )
                        missing_sheets = sorted(
                            set(expected_sheets) - set(workbook.sheet_names)
                        )
                        extra_sheets = sorted(
                            set(workbook.sheet_names) - set(expected_sheets)
                        )
                        if missing_sheets or extra_sheets:
                            raise ValueError(
                                "Workbook worksheets must match observed strata exactly. "
                                f"Missing: {missing_sheets or 'none'}; "
                                f"unexpected: {extra_sheets or 'none'}."
                            )
                        matrices = {}
                        for sheet_name, stratum_value in expected_sheets.items():
                            matrix = pd.read_excel(
                                workbook, sheet_name=sheet_name, index_col=0
                            )
                            if (
                                matrix.empty
                                or not matrix.index.is_unique
                                or not matrix.columns.is_unique
                            ):
                                raise ValueError(
                                    f"Worksheet {sheet_name!r} must be a non-empty "
                                    "matrix with unique PSU row and column labels."
                                )
                            stratum_ids = (
                                df.loc[df[ppswor_strata] == stratum_value, ppswor_psu]
                                .dropna().tolist()
                            )
                            label_lookup = {str(value): value for value in stratum_ids}
                            matrix.index = [
                                label_lookup.get(str(value), value)
                                for value in matrix.index
                            ]
                            matrix.columns = [
                                label_lookup.get(str(value), value)
                                for value in matrix.columns
                            ]
                            if set(matrix.index) != set(matrix.columns):
                                raise ValueError(
                                    f"Worksheet {sheet_name!r} row and column PSU "
                                    "labels must match."
                                )
                            ordered_ids = list(dict.fromkeys(stratum_ids))
                            matrices[stratum_value] = matrix.loc[
                                ordered_ids, ordered_ids
                            ]
                        joint_probabilities = matrices
                    else:
                        matrix = pd.read_csv(
                            io.BytesIO(matrix_bytes), index_col=0
                        )
                        if (
                            matrix.empty
                            or not matrix.index.is_unique
                            or not matrix.columns.is_unique
                        ):
                            raise ValueError(
                                "The joint-inclusion CSV must be a non-empty matrix "
                                "with unique PSU row and column labels."
                            )
                        sampled_ids = df[ppswor_psu].dropna().tolist()
                        label_lookup = {str(value): value for value in sampled_ids}
                        matrix.index = [
                            label_lookup.get(str(value), value)
                            for value in matrix.index
                        ]
                        matrix.columns = [
                            label_lookup.get(str(value), value)
                            for value in matrix.columns
                        ]
                        if set(matrix.index) != set(matrix.columns):
                            raise ValueError(
                                "Joint-inclusion matrix row and column PSU labels must match."
                            )
                        ordered_ids = list(dict.fromkeys(sampled_ids))
                        joint_probabilities = matrix.loc[ordered_ids, ordered_ids]
                    ppswor_result = run_ppswor_total_service(
                        df, ppswor_outcome, ppswor_psu, ppswor_pi,
                        joint_probabilities, ppswor_strata, ppswor_confidence,
                    )
                    st.session_state["ppswor_total_result"] = ppswor_result
                    st.session_state["ppswor_total_result_key"] = (
                        _dataset_analysis_key(df), ppswor_psu, ppswor_outcome,
                        ppswor_pi, ppswor_stratification, ppswor_strata,
                        ppswor_confidence, matrix_digest,
                    )
                except (
                    TypeError, ValueError, KeyError, pd.errors.ParserError,
                    ImportError,
                ) as exc:
                    st.error(str(exc))
            ppswor_result_key = (
                _dataset_analysis_key(df), ppswor_psu, ppswor_outcome,
                ppswor_pi, ppswor_stratification, ppswor_strata,
                ppswor_confidence,
                hashlib.sha256(ppswor_matrix_file.getvalue()).hexdigest()
                if ppswor_matrix_file is not None else None,
            )
            saved_ppswor = st.session_state.get("ppswor_total_result")
            if (
                saved_ppswor is not None
                and st.session_state.get("ppswor_total_result_key") == ppswor_result_key
            ):
                st.metric(
                    "PPSWOR estimated population total",
                    f"{saved_ppswor.metadata['estimate']:,.4g}",
                )
                st.metric(
                    "SYG design-based standard error",
                    f"{saved_ppswor.metadata['standard_error']:,.4g}",
                )
                ci = saved_ppswor.metadata["confidence_interval"]
                st.write(
                    f"{ppswor_confidence:.0%} confidence interval: "
                    f"[{ci[0]:,.4g}, {ci[1]:,.4g}]"
                )
                st.dataframe(
                    saved_ppswor.tables["stratum_estimates"],
                    hide_index=True, use_container_width=True,
                )
                with st.expander("Pairwise SYG variance contributions"):
                    st.dataframe(
                        saved_ppswor.tables["pairwise_variance"],
                        hide_index=True, use_container_width=True,
                    )
                st.download_button(
                    "Download PPSWOR total report (PDF)",
                    data=build_ppswor_report(saved_ppswor),
                    file_name="timanstat_ppswor_total_report.pdf",
                    mime="application/pdf",
                    key="download_ppswor_total_report",
                )
                for warning in saved_ppswor.limitations:
                    st.warning(warning)

            with st.expander("PPSWOR population mean and proportion estimation"):
                st.write(
                    "Estimate a population mean or proportion from fully observed "
                    "PSU-level numerator and denominator totals. The point estimate "
                    "is a ratio of Horvitz–Thompson totals; variance uses first-order "
                    "Taylor linearisation with the Sen–Yates–Grundy estimator."
                )
                st.warning(
                    "This is PSU-level ratio estimation, not a two-stage estimator. "
                    "Use actual first- and second-order PPSWOR inclusion probabilities. "
                    "For a proportion, each PSU numerator must be between zero and "
                    "its denominator. For a mean, the denominator is typically a "
                    "PSU population count or eligible-unit total."
                )
                ppswor_ratio_numerator_options = [
                    x for x in ppswor_numeric if x != ppswor_pi
                ]
                ppswor_ratio_numerator = st.selectbox(
                    "PSU numerator total", ppswor_ratio_numerator_options,
                    key="ppswor_ratio_numerator",
                )
                ppswor_ratio_denominator_options = [
                    x for x in ppswor_numeric
                    if x not in (ppswor_pi, ppswor_ratio_numerator)
                ]
                ppswor_ratio_denominator = st.selectbox(
                    "PSU denominator total", ppswor_ratio_denominator_options,
                    key="ppswor_ratio_denominator",
                )
                ppswor_ratio_parameter = st.radio(
                    "Ratio parameter", ["Mean", "Proportion"],
                    horizontal=True, key="ppswor_ratio_parameter",
                )
                ppswor_ratio_ready = (
                    ppswor_matrix_file is not None
                    and ppswor_ratio_numerator is not None
                    and ppswor_ratio_denominator is not None
                    and len({
                        ppswor_psu, ppswor_pi, ppswor_ratio_numerator,
                        ppswor_ratio_denominator,
                    }) == 4
                    and (
                        ppswor_stratification == "Unstratified"
                        or ppswor_strata is not None
                    )
                )
                if st.button(
                    "Run PPSWOR mean / proportion",
                    type="primary", key="run_ppswor_ratio",
                    disabled=not ppswor_ratio_ready,
                ):
                    try:
                        ratio_matrix_bytes = ppswor_matrix_file.getvalue()
                        ratio_matrix_digest = hashlib.sha256(
                            ratio_matrix_bytes
                        ).hexdigest()
                        if ppswor_stratification == "Stratified":
                            ratio_workbook = pd.ExcelFile(
                                io.BytesIO(ratio_matrix_bytes)
                            )
                            ratio_strata_values = (
                                df[ppswor_strata].dropna().unique().tolist()
                            )
                            ratio_sheet_map = {
                                str(value): value for value in ratio_strata_values
                            }
                            if len(ratio_sheet_map) != len(ratio_strata_values):
                                raise ValueError(
                                    "Stratum labels must have unique text "
                                    "representations for worksheet matching."
                                )
                            if set(ratio_workbook.sheet_names) != set(ratio_sheet_map):
                                raise ValueError(
                                    "Workbook worksheets must match observed strata "
                                    "exactly for ratio estimation."
                                )
                            ratio_matrices = {}
                            for sheet_name, stratum_value in ratio_sheet_map.items():
                                ratio_matrix = pd.read_excel(
                                    ratio_workbook, sheet_name=sheet_name, index_col=0
                                )
                                if (
                                    ratio_matrix.empty
                                    or not ratio_matrix.index.is_unique
                                    or not ratio_matrix.columns.is_unique
                                ):
                                    raise ValueError(
                                        f"Worksheet {sheet_name!r} must have unique "
                                        "PSU row and column labels."
                                    )
                                ratio_ids = (
                                    df.loc[
                                        df[ppswor_strata] == stratum_value,
                                        ppswor_psu,
                                    ].dropna().tolist()
                                )
                                ratio_lookup = {
                                    str(value): value for value in ratio_ids
                                }
                                ratio_matrix.index = [
                                    ratio_lookup.get(str(value), value)
                                    for value in ratio_matrix.index
                                ]
                                ratio_matrix.columns = [
                                    ratio_lookup.get(str(value), value)
                                    for value in ratio_matrix.columns
                                ]
                                unique_ratio_ids = list(dict.fromkeys(ratio_ids))
                                if (
                                    ratio_matrix.shape != (
                                        len(unique_ratio_ids), len(unique_ratio_ids)
                                    )
                                    or set(ratio_matrix.index) != set(unique_ratio_ids)
                                    or set(ratio_matrix.columns) != set(unique_ratio_ids)
                                ):
                                    raise ValueError(
                                        f"Worksheet {sheet_name!r} must be a square "
                                        "matrix covering exactly the sampled PSUs "
                                        "in that stratum."
                                    )
                                ratio_matrices[stratum_value] = ratio_matrix.loc[
                                    unique_ratio_ids, unique_ratio_ids
                                ]
                            ratio_joint_probabilities = ratio_matrices
                        else:
                            ratio_matrix = pd.read_csv(
                                io.BytesIO(ratio_matrix_bytes), index_col=0
                            )
                            if (
                                ratio_matrix.empty
                                or not ratio_matrix.index.is_unique
                                or not ratio_matrix.columns.is_unique
                            ):
                                raise ValueError(
                                    "The joint-inclusion CSV must have unique PSU "
                                    "row and column labels."
                                )
                            ratio_ids = df[ppswor_psu].dropna().tolist()
                            ratio_lookup = {str(value): value for value in ratio_ids}
                            ratio_matrix.index = [
                                ratio_lookup.get(str(value), value)
                                for value in ratio_matrix.index
                            ]
                            ratio_matrix.columns = [
                                ratio_lookup.get(str(value), value)
                                for value in ratio_matrix.columns
                            ]
                            unique_ratio_ids = list(dict.fromkeys(ratio_ids))
                            if (
                                ratio_matrix.shape != (
                                    len(unique_ratio_ids), len(unique_ratio_ids)
                                )
                                or set(ratio_matrix.index) != set(unique_ratio_ids)
                                or set(ratio_matrix.columns) != set(unique_ratio_ids)
                            ):
                                raise ValueError(
                                    "The joint-inclusion CSV must be a square matrix "
                                    "covering exactly the sampled PSUs."
                                )
                            ratio_joint_probabilities = ratio_matrix.loc[
                                unique_ratio_ids, unique_ratio_ids
                            ]
                        ratio_result = run_ppswor_ratio_service(
                            df, ppswor_ratio_numerator, ppswor_ratio_denominator,
                            ppswor_psu, ppswor_pi, ratio_joint_probabilities,
                            ppswor_strata, ppswor_confidence,
                            ppswor_ratio_parameter.lower(),
                        )
                        st.session_state["ppswor_ratio_result"] = ratio_result
                        st.session_state["ppswor_ratio_result_key"] = (
                            _dataset_analysis_key(df), ppswor_psu, ppswor_pi,
                            ppswor_ratio_numerator, ppswor_ratio_denominator,
                            ppswor_ratio_parameter, ppswor_stratification,
                            ppswor_strata, ppswor_confidence, ratio_matrix_digest,
                        )
                    except (
                        TypeError, ValueError, KeyError, pd.errors.ParserError,
                        ImportError,
                    ) as exc:
                        st.error(str(exc))
                ppswor_ratio_result_key = (
                    _dataset_analysis_key(df), ppswor_psu, ppswor_pi,
                    ppswor_ratio_numerator, ppswor_ratio_denominator,
                    ppswor_ratio_parameter, ppswor_stratification,
                    ppswor_strata, ppswor_confidence,
                    hashlib.sha256(ppswor_matrix_file.getvalue()).hexdigest()
                    if ppswor_matrix_file is not None else None,
                )
                saved_ppswor_ratio = st.session_state.get("ppswor_ratio_result")
                if (
                    saved_ppswor_ratio is not None
                    and st.session_state.get("ppswor_ratio_result_key")
                    == ppswor_ratio_result_key
                ):
                    ratio_estimate = saved_ppswor_ratio.metadata["estimate"]
                    if ppswor_ratio_parameter == "Proportion":
                        st.metric(
                            "PPSWOR estimated population proportion",
                            f"{ratio_estimate:.2%}",
                        )
                    else:
                        st.metric(
                            "PPSWOR estimated population mean",
                            f"{ratio_estimate:,.4g}",
                        )
                    st.metric(
                        "Taylor-linearised SYG standard error",
                        f"{saved_ppswor_ratio.metadata['standard_error']:,.4g}",
                    )
                    ratio_ci = saved_ppswor_ratio.metadata["confidence_interval"]
                    if ppswor_ratio_parameter == "Proportion":
                        st.write(
                            f"{ppswor_confidence:.0%} confidence interval: "
                            f"[{ratio_ci[0]:.2%}, {ratio_ci[1]:.2%}]"
                        )
                    else:
                        st.write(
                            f"{ppswor_confidence:.0%} confidence interval: "
                            f"[{ratio_ci[0]:,.4g}, {ratio_ci[1]:,.4g}]"
                        )
                    st.dataframe(
                        saved_ppswor_ratio.tables["stratum_estimates"],
                        hide_index=True, use_container_width=True,
                    )
                    with st.expander("Ratio pairwise SYG variance contributions"):
                        st.dataframe(
                            saved_ppswor_ratio.tables["pairwise_variance"],
                            hide_index=True, use_container_width=True,
                        )
                    st.download_button(
                        "Download PPSWOR mean/proportion report (PDF)",
                        data=build_ppswor_report(saved_ppswor_ratio),
                        file_name="timanstat_ppswor_ratio_report.pdf",
                        mime="application/pdf",
                        key="download_ppswor_ratio_report",
                    )
                    for warning in saved_ppswor_ratio.limitations:
                        st.warning(warning)


            with st.expander("PPSWOR domain mean and proportion estimation"):
                st.write(
                    "Estimate a mean or proportion for a subpopulation using "
                    "domain-specific PSU numerator and denominator totals. The "
                    "original sample and full joint-inclusion matrices are retained "
                    "for Taylor-linearised SYG variance estimation."
                )
                st.warning(
                    "Prepare domain-specific numerator and denominator totals for "
                    "every sampled PSU, including explicit zeros where a PSU has no "
                    "members of the domain. Do not filter the dataset to domain "
                    "members or remove zero-domain PSUs. This interface expects "
                    "PSU-level aggregates, not respondent-level domain flags."
                )
                ppswor_domain_name = st.text_input(
                    "Domain label (e.g. Women aged 18–24)",
                    key="ppswor_domain_name",
                )
                ppswor_domain_num_options = [
                    x for x in ppswor_numeric if x != ppswor_pi
                ]
                ppswor_domain_num = st.selectbox(
                    "Domain-specific PSU numerator total",
                    ppswor_domain_num_options,
                    key="ppswor_domain_numerator",
                )
                ppswor_domain_den_options = [
                    x for x in ppswor_numeric
                    if x not in (ppswor_pi, ppswor_domain_num)
                ]
                ppswor_domain_den = st.selectbox(
                    "Domain-specific PSU denominator total",
                    ppswor_domain_den_options,
                    key="ppswor_domain_denominator",
                )
                ppswor_domain_parameter = st.radio(
                    "Domain parameter", ["Mean", "Proportion"],
                    horizontal=True, key="ppswor_domain_parameter",
                )
                ppswor_domain_ready = (
                    bool(ppswor_domain_name.strip())
                    and ppswor_matrix_file is not None
                    and ppswor_domain_num is not None
                    and ppswor_domain_den is not None
                    and len({
                        ppswor_psu, ppswor_pi,
                        ppswor_domain_num, ppswor_domain_den,
                    }) == 4
                    and (
                        ppswor_stratification == "Unstratified"
                        or ppswor_strata is not None
                    )
                )
                if st.button(
                    "Run PPSWOR domain estimate",
                    type="primary", key="run_ppswor_domain",
                    disabled=not ppswor_domain_ready,
                ):
                    try:
                        domain_matrix_bytes = ppswor_matrix_file.getvalue()
                        domain_matrix_digest = hashlib.sha256(
                            domain_matrix_bytes
                        ).hexdigest()
                        if ppswor_stratification == "Stratified":
                            domain_workbook = pd.ExcelFile(
                                io.BytesIO(domain_matrix_bytes)
                            )
                            domain_strata_values = (
                                df[ppswor_strata].dropna().unique().tolist()
                            )
                            domain_sheet_map = {
                                str(value): value for value in domain_strata_values
                            }
                            if len(domain_sheet_map) != len(domain_strata_values):
                                raise ValueError(
                                    "Stratum labels must have unique text "
                                    "representations for worksheet matching."
                                )
                            if set(domain_workbook.sheet_names) != set(domain_sheet_map):
                                raise ValueError(
                                    "Workbook worksheets must match observed strata "
                                    "exactly for domain estimation."
                                )
                            domain_matrices = {}
                            for sheet_name, stratum_value in domain_sheet_map.items():
                                domain_matrix = pd.read_excel(
                                    domain_workbook, sheet_name=sheet_name, index_col=0
                                )
                                if (
                                    domain_matrix.empty
                                    or not domain_matrix.index.is_unique
                                    or not domain_matrix.columns.is_unique
                                ):
                                    raise ValueError(
                                        f"Worksheet {sheet_name!r} must have unique "
                                        "PSU row and column labels."
                                    )
                                domain_ids = (
                                    df.loc[
                                        df[ppswor_strata] == stratum_value,
                                        ppswor_psu,
                                    ].dropna().tolist()
                                )
                                domain_lookup = {
                                    str(value): value for value in domain_ids
                                }
                                domain_matrix.index = [
                                    domain_lookup.get(str(value), value)
                                    for value in domain_matrix.index
                                ]
                                domain_matrix.columns = [
                                    domain_lookup.get(str(value), value)
                                    for value in domain_matrix.columns
                                ]
                                unique_domain_ids = list(dict.fromkeys(domain_ids))
                                if (
                                    domain_matrix.shape != (
                                        len(unique_domain_ids), len(unique_domain_ids)
                                    )
                                    or set(domain_matrix.index) != set(unique_domain_ids)
                                    or set(domain_matrix.columns) != set(unique_domain_ids)
                                ):
                                    raise ValueError(
                                        f"Worksheet {sheet_name!r} must be square "
                                        "and cover every sampled PSU in that stratum, "
                                        "including PSUs with zero domain totals."
                                    )
                                domain_matrices[stratum_value] = domain_matrix.loc[
                                    unique_domain_ids, unique_domain_ids
                                ]
                            domain_joint_probabilities = domain_matrices
                        else:
                            domain_matrix = pd.read_csv(
                                io.BytesIO(domain_matrix_bytes), index_col=0
                            )
                            if (
                                domain_matrix.empty
                                or not domain_matrix.index.is_unique
                                or not domain_matrix.columns.is_unique
                            ):
                                raise ValueError(
                                    "The joint-inclusion CSV must have unique PSU "
                                    "row and column labels."
                                )
                            domain_ids = df[ppswor_psu].dropna().tolist()
                            domain_lookup = {
                                str(value): value for value in domain_ids
                            }
                            domain_matrix.index = [
                                domain_lookup.get(str(value), value)
                                for value in domain_matrix.index
                            ]
                            domain_matrix.columns = [
                                domain_lookup.get(str(value), value)
                                for value in domain_matrix.columns
                            ]
                            unique_domain_ids = list(dict.fromkeys(domain_ids))
                            if (
                                domain_matrix.shape != (
                                    len(unique_domain_ids), len(unique_domain_ids)
                                )
                                or set(domain_matrix.index) != set(unique_domain_ids)
                                or set(domain_matrix.columns) != set(unique_domain_ids)
                            ):
                                raise ValueError(
                                    "The joint-inclusion CSV must be square and cover "
                                    "every sampled PSU, including zero-domain PSUs."
                                )
                            domain_joint_probabilities = domain_matrix.loc[
                                unique_domain_ids, unique_domain_ids
                            ]
                        domain_result = run_ppswor_domain_ratio_service(
                            df, ppswor_domain_name.strip(),
                            ppswor_domain_num, ppswor_domain_den,
                            ppswor_psu, ppswor_pi, domain_joint_probabilities,
                            ppswor_strata, ppswor_confidence,
                            ppswor_domain_parameter.lower(),
                        )
                        st.session_state["ppswor_domain_result"] = domain_result
                        st.session_state["ppswor_domain_result_key"] = (
                            _dataset_analysis_key(df), ppswor_domain_name.strip(),
                            ppswor_psu, ppswor_pi, ppswor_domain_num,
                            ppswor_domain_den, ppswor_domain_parameter,
                            ppswor_stratification, ppswor_strata,
                            ppswor_confidence, domain_matrix_digest,
                        )
                    except (
                        TypeError, ValueError, KeyError, pd.errors.ParserError,
                        ImportError,
                    ) as exc:
                        st.error(str(exc))
                ppswor_domain_result_key = (
                    _dataset_analysis_key(df), ppswor_domain_name.strip(),
                    ppswor_psu, ppswor_pi, ppswor_domain_num,
                    ppswor_domain_den, ppswor_domain_parameter,
                    ppswor_stratification, ppswor_strata, ppswor_confidence,
                    hashlib.sha256(ppswor_matrix_file.getvalue()).hexdigest()
                    if ppswor_matrix_file is not None else None,
                )
                saved_ppswor_domain = st.session_state.get("ppswor_domain_result")
                if (
                    saved_ppswor_domain is not None
                    and st.session_state.get("ppswor_domain_result_key")
                    == ppswor_domain_result_key
                ):
                    domain_estimate = saved_ppswor_domain.metadata["estimate"]
                    if ppswor_domain_parameter == "Proportion":
                        st.metric(
                            f"Estimated proportion — {ppswor_domain_name.strip()}",
                            f"{domain_estimate:.2%}",
                        )
                    else:
                        st.metric(
                            f"Estimated mean — {ppswor_domain_name.strip()}",
                            f"{domain_estimate:,.4g}",
                        )
                    st.metric(
                        "Domain Taylor-linearised SYG standard error",
                        f"{saved_ppswor_domain.metadata['standard_error']:,.4g}",
                    )
                    domain_ci = saved_ppswor_domain.metadata["confidence_interval"]
                    if ppswor_domain_parameter == "Proportion":
                        st.write(
                            f"{ppswor_confidence:.0%} confidence interval: "
                            f"[{domain_ci[0]:.2%}, {domain_ci[1]:.2%}]"
                        )
                    else:
                        st.write(
                            f"{ppswor_confidence:.0%} confidence interval: "
                            f"[{domain_ci[0]:,.4g}, {domain_ci[1]:,.4g}]"
                        )
                    st.caption(
                        "Precision diagnostics are descriptive. The coefficient of "
                        "variation is SE divided by the absolute estimate; it is not "
                        "a universal pass/fail threshold."
                    )
                    st.dataframe(
                        saved_ppswor_domain.tables["diagnostics"],
                        hide_index=True, use_container_width=True,
                    )
                    st.dataframe(
                        saved_ppswor_domain.tables["stratum_estimates"],
                        hide_index=True, use_container_width=True,
                    )
                    with st.expander("Domain pairwise SYG variance contributions"):
                        st.dataframe(
                            saved_ppswor_domain.tables["pairwise_variance"],
                            hide_index=True, use_container_width=True,
                        )
                    st.download_button(
                        "Download PPSWOR domain mean/proportion report (PDF)",
                        data=build_ppswor_report(saved_ppswor_domain),
                        file_name="timanstat_ppswor_domain_ratio_report.pdf",
                        mime="application/pdf",
                        key="download_ppswor_domain_ratio_report",
                    )
                    for warning in saved_ppswor_domain.limitations:
                        st.warning(warning)


            with st.expander("PPSWOR domain total estimation"):
                st.write(
                    "Estimate a subpopulation total using domain-specific PSU totals "
                                       "and the original fixed-size PPSWOR design. The "
                    "Horvitz–Thompson expansion and Sen–Yates–Grundy variance retain "
                    "all sampled PSUs and their complete joint-inclusion matrix."
                )
                st.warning(
                    "Supply the domain-specific total for every sampled PSU, including "
                    "an explicit zero for PSUs with no members of the domain. Do not "
                    "filter the dataset or joint-inclusion matrix to domain-positive PSUs. "
                    "This is a PSU-level estimator and does not support SSU subsampling."
                )
                ppswor_domain_total_name = st.text_input(
                    "Domain label for total estimation",
                    key="ppswor_domain_total_name",
                )
                ppswor_domain_total_options = [
                    x for x in ppswor_numeric if x != ppswor_pi
                ]
                ppswor_domain_total_variable = st.selectbox(
                    "Domain-specific fully observed PSU total",
                    ppswor_domain_total_options,
                    key="ppswor_domain_total_variable",
                )
                ppswor_domain_total_ready = (
                    bool(ppswor_domain_total_name.strip())
                    and ppswor_matrix_file is not None
                    and ppswor_domain_total_variable is not None
                    and ppswor_domain_total_variable not in (ppswor_psu, ppswor_pi)
                    and (
                        ppswor_stratification == "Unstratified"
                        or ppswor_strata is not None
                    )
                )
                if st.button(
                    "Run PPSWOR domain total",
                    type="primary", key="run_ppswor_domain_total",
                    disabled=not ppswor_domain_total_ready,
                ):
                    try:
                        domain_total_matrix_bytes = ppswor_matrix_file.getvalue()
                        domain_total_matrix_digest = hashlib.sha256(
                            domain_total_matrix_bytes
                        ).hexdigest()
                        if ppswor_stratification == "Stratified":
                            domain_total_workbook = pd.ExcelFile(
                                io.BytesIO(domain_total_matrix_bytes)
                            )
                            domain_total_strata_values = (
                                df[ppswor_strata].dropna().unique().tolist()
                            )
                            domain_total_sheet_map = {
                                str(value): value
                                for value in domain_total_strata_values
                            }
                            if len(domain_total_sheet_map) != len(domain_total_strata_values):
                                raise ValueError(
                                    "Stratum labels must have unique text representations "
                                    "for worksheet matching."
                                )
                            if set(domain_total_workbook.sheet_names) != set(domain_total_sheet_map):
                                raise ValueError(
                                    "Workbook worksheets must match observed strata exactly "
                                    "for domain total estimation."
                                )
                            domain_total_matrices = {}
                            for sheet_name, stratum_value in domain_total_sheet_map.items():
                                domain_total_matrix = pd.read_excel(
                                    domain_total_workbook,
                                    sheet_name=sheet_name,
                                    index_col=0,
                                )
                                if (
                                    domain_total_matrix.empty
                                    or not domain_total_matrix.index.is_unique
                                    or not domain_total_matrix.columns.is_unique
                                ):
                                    raise ValueError(
                                        f"Worksheet {sheet_name!r} must have unique PSU "
                                        "row and column labels."
                                    )
                                domain_total_ids = (
                                    df.loc[
                                        df[ppswor_strata] == stratum_value,
                                        ppswor_psu,
                                    ].dropna().tolist()
                                )
                                domain_total_lookup = {
                                    str(value): value for value in domain_total_ids
                                }
                                domain_total_matrix.index = [
                                    domain_total_lookup.get(str(value), value)
                                    for value in domain_total_matrix.index
                                ]
                                domain_total_matrix.columns = [
                                    domain_total_lookup.get(str(value), value)
                                    for value in domain_total_matrix.columns
                                ]
                                unique_domain_total_ids = list(
                                    dict.fromkeys(domain_total_ids)
                                )
                                if (
                                    domain_total_matrix.shape
                                    != (
                                        len(unique_domain_total_ids),
                                        len(unique_domain_total_ids),
                                    )
                                    or set(domain_total_matrix.index)
                                    != set(unique_domain_total_ids)
                                    or set(domain_total_matrix.columns)
                                    != set(unique_domain_total_ids)
                                ):
                                    raise ValueError(
                                        f"Worksheet {sheet_name!r} must be square and cover "
                                        "every sampled PSU in that stratum, including "
                                        "zero-domain PSUs."
                                    )
                                domain_total_matrices[stratum_value] = (
                                    domain_total_matrix.loc[
                                        unique_domain_total_ids,
                                        unique_domain_total_ids,
                                    ]
                                )
                            domain_total_joint_probabilities = domain_total_matrices
                        else:
                            domain_total_matrix = pd.read_csv(
                                io.BytesIO(domain_total_matrix_bytes),
                                index_col=0,
                            )
                            if (
                                domain_total_matrix.empty
                                or not domain_total_matrix.index.is_unique
                                or not domain_total_matrix.columns.is_unique
                            ):
                                raise ValueError(
                                    "The joint-inclusion CSV must have unique PSU "
                                    "row and column labels."
                                )
                            domain_total_ids = df[ppswor_psu].dropna().tolist()
                            domain_total_lookup = {
                                str(value): value for value in domain_total_ids
                            }
                            domain_total_matrix.index = [
                                domain_total_lookup.get(str(value), value)
                                for value in domain_total_matrix.index
                            ]
                            domain_total_matrix.columns = [
                                domain_total_lookup.get(str(value), value)
                                for value in domain_total_matrix.columns
                            ]
                            unique_domain_total_ids = list(
                                dict.fromkeys(domain_total_ids)
                            )
                            if (
                                domain_total_matrix.shape
                                != (
                                    len(unique_domain_total_ids),
                                    len(unique_domain_total_ids),
                                )
                                or set(domain_total_matrix.index)
                                != set(unique_domain_total_ids)
                                or set(domain_total_matrix.columns)
                                != set(unique_domain_total_ids)
                            ):
                                raise ValueError(
                                    "The joint-inclusion CSV must be square and cover "
                                    "every sampled PSU, including zero-domain PSUs."
                                )
                            domain_total_joint_probabilities = (
                                domain_total_matrix.loc[
                                    unique_domain_total_ids,
                                    unique_domain_total_ids,
                                ]
                            )
                        domain_total_result = run_ppswor_domain_total_service(
                            df,
                            ppswor_domain_total_name.strip(),
                            ppswor_domain_total_variable,
                            ppswor_psu,
                            ppswor_pi,
                            domain_total_joint_probabilities,
                            ppswor_strata,
                            ppswor_confidence,
                        )
                        st.session_state["ppswor_domain_total_result"] = (
                            domain_total_result
                        )
                        st.session_state["ppswor_domain_total_result_key"] = (
                            _dataset_analysis_key(df),
                            ppswor_domain_total_name.strip(),
                            ppswor_psu,
                            ppswor_pi,
                            ppswor_domain_total_variable,
                            ppswor_stratification,
                            ppswor_strata,
                            ppswor_confidence,
                            domain_total_matrix_digest,
                        )
                    except (
                        TypeError, ValueError, KeyError, pd.errors.ParserError,
                        ImportError,
                    ) as exc:
                        st.error(str(exc))

                ppswor_domain_total_result_key = (
                    _dataset_analysis_key(df),
                    ppswor_domain_total_name.strip(),
                    ppswor_psu,
                    ppswor_pi,
                    ppswor_domain_total_variable,
                    ppswor_stratification,
                    ppswor_strata,
                    ppswor_confidence,
                    hashlib.sha256(ppswor_matrix_file.getvalue()).hexdigest()
                    if ppswor_matrix_file is not None else None,
                )
                saved_ppswor_domain_total = st.session_state.get(
                    "ppswor_domain_total_result"
                )
                if (
                    saved_ppswor_domain_total is not None
                    and st.session_state.get("ppswor_domain_total_result_key")
                    == ppswor_domain_total_result_key
                ):
                    st.metric(
                        f"Estimated domain total — {ppswor_domain_total_name.strip()}",
                        f"{saved_ppswor_domain_total.metadata['estimate']:,.4g}",
                    )
                    st.metric(
                        "Domain SYG standard error",
                        f"{saved_ppswor_domain_total.metadata['standard_error']:,.4g}",
                    )
                    domain_total_ci = (
                        saved_ppswor_domain_total.metadata["confidence_interval"]
                    )
                    st.write(
                        f"{ppswor_confidence:.0%} confidence interval: "
                        f"[{domain_total_ci[0]:,.4g}, {domain_total_ci[1]:,.4g}]"
                    )
                    st.caption(
                        "Precision diagnostics are descriptive. The coefficient of "
                        "variation is SE divided by the absolute estimate; it is not "
                        "a universal pass/fail threshold."
                    )
                    st.dataframe(
                        saved_ppswor_domain_total.tables["diagnostics"],
                        hide_index=True,
                        use_container_width=True,
                    )
                    st.dataframe(
                        saved_ppswor_domain_total.tables["stratum_estimates"],
                        hide_index=True,
                        use_container_width=True,
                    )
                    with st.expander(
                        "Domain total pairwise SYG variance contributions"
                    ):
                        st.dataframe(
                            saved_ppswor_domain_total.tables["pairwise_variance"],
                            hide_index=True,
                            use_container_width=True,
                        )
                    st.download_button(
                        "Download PPSWOR domain total report (PDF)",
                        data=build_ppswor_report(saved_ppswor_domain_total),
                        file_name="timanstat_ppswor_domain_total_report.pdf",
                        mime="application/pdf",
                        key="download_ppswor_domain_total_report",
                    )
                    for warning in saved_ppswor_domain_total.limitations:
                        st.warning(warning)

        with st.expander("Survey sample size and sampling design planner", expanded=False):
            from timan_intelligence.services.analysis_service import (
                run_sample_size_service,
                run_stratified_allocation_service,
                run_cluster_sample_plan_service,
            )

            st.write(
                "Plan a survey before fieldwork. Supply the expected prevalence or "
                "standard deviation, precision, population size and design assumptions. "
                "These are planning calculations, not substitutes for a complete "
                "analysis-specific design review."
            )
            planner_parameter = st.selectbox(
                "Primary parameter", ["Proportion", "Mean"],
                key="sample_planner_parameter",
            )
            planner_confidence = st.selectbox(
                "Confidence level", [0.90, 0.95, 0.99], index=1,
                format_func=lambda value: f"{value:.0%}",
                key="sample_planner_confidence",
            )
            planner_error = st.number_input(
                "Margin of error (absolute)", min_value=0.001,
                max_value=0.99 if planner_parameter == "Proportion" else 1000000.0,
                value=0.05 if planner_parameter == "Proportion" else 1.0,
                step=0.01, key="sample_planner_error",
            )
            planner_population = st.number_input(
                "Target population size (0 = large/unknown)", min_value=0,
                value=0, step=100, key="sample_planner_population",
            )
            planner_prevalence = 0.5
            planner_sd = None
            if planner_parameter == "Proportion":
                planner_prevalence = st.number_input(
                    "Expected prevalence/proportion", min_value=0.0,
                    max_value=1.0, value=0.5, step=0.05,
                    key="sample_planner_prevalence",
                )
            else:
                planner_sd = st.number_input(
                    "Expected standard deviation", min_value=0.000001,
                    value=10.0, step=0.5, key="sample_planner_sd",
                )
            planner_deff = st.number_input(
                "Design effect", min_value=0.01, value=1.0, step=0.1,
                key="sample_planner_deff",
            )
            planner_nonresponse = st.number_input(
                "Expected nonresponse rate", min_value=0.0, max_value=0.99,
                value=0.10, step=0.01, key="sample_planner_nonresponse",
            )
            if st.button("Calculate required sample size", key="run_sample_size"):
                try:
                    args = {
                        "parameter": planner_parameter.lower(),
                        "confidence_level": planner_confidence,
                        "margin_of_error": planner_error,
                        "population_size": int(planner_population) or None,
                        "design_effect": planner_deff,
                        "nonresponse_rate": planner_nonresponse,
                    }
                    if planner_parameter == "Proportion":
                        args["prevalence"] = planner_prevalence
                    else:
                        args["standard_deviation"] = planner_sd
                    result = run_sample_size_service(**args)
                    st.session_state["sample_size_plan_result"] = result
                except (TypeError, ValueError, KeyError) as exc:
                    st.error(str(exc))
            sample_plan = st.session_state.get("sample_size_plan_result")
            if sample_plan is not None:
                st.metric("Recommended sample to approach", f"{sample_plan.metadata['recommended_sample_size']:,}")
                st.dataframe(sample_plan.tables["calculation"], hide_index=True, use_container_width=True)
                for assumption in sample_plan.assumptions:
                    st.caption(f"Assumption: {assumption}")
                for warning in sample_plan.limitations:
                    st.warning(warning)

            st.divider()
            st.markdown("**Stratified sample allocation**")
            st.caption("Upload a CSV with one row per stratum and a positive population count.")
            allocation_file = st.file_uploader(
                "Stratum population CSV", type=["csv"],
                key="sample_allocation_upload",
            )
            if allocation_file is not None:
                try:
                    allocation_frame = pd.read_csv(allocation_file)
                    allocation_population_col = st.selectbox(
                        "Stratum population column", allocation_frame.columns,
                        key="sample_allocation_population_col",
                    )
                    allocation_method = st.selectbox(
                        "Allocation method", ["proportional", "equal", "neyman"],
                        key="sample_allocation_method",
                    )
                    allocation_sd_col = None
                    allocation_cost_col = None
                    if allocation_method == "neyman":
                        allocation_sd_col = st.selectbox(
                            "Within-stratum standard deviation",
                            [col for col in allocation_frame.columns if col != allocation_population_col],
                            key="sample_allocation_sd_col",
                        )
                        allocation_cost_col = st.selectbox(
                            "Optional relative fieldwork cost",
                            ["None"] + [col for col in allocation_frame.columns if col not in (allocation_population_col, allocation_sd_col)],
                            key="sample_allocation_cost_col",
                        )
                    allocation_total = st.number_input(
                        "Total sample to allocate", min_value=1,
                        value=100, step=10, key="sample_allocation_total",
                    )
                    if st.button("Allocate sample by stratum", key="run_sample_allocation"):
                        result = run_stratified_allocation_service(
                            allocation_frame, int(allocation_total),
                            allocation=allocation_method,
                            population_column=allocation_population_col,
                            standard_deviation_column=allocation_sd_col,
                            cost_column=None if allocation_cost_col in (None, "None") else allocation_cost_col,
                        )
                        st.session_state["sample_allocation_result"] = result
                    allocation_result = st.session_state.get("sample_allocation_result")
                    if allocation_result is not None:
                        st.dataframe(allocation_result.tables["stratum_allocation"], hide_index=True, use_container_width=True)
                        st.download_button(
                            "Download stratum allocation (CSV)",
                            data=allocation_result.tables["stratum_allocation"].to_csv(index=False).encode("utf-8"),
                            file_name="timanstat_stratum_sample_allocation.csv",
                            mime="text/csv", key="download_sample_allocation",
                        )
                except (TypeError, ValueError, KeyError, pd.errors.ParserError) as exc:
                    st.error(str(exc))

            st.divider()
            st.markdown("**Cluster sample planning**")
            cluster_col1, cluster_col2 = st.columns(2)
            with cluster_col1:
                cluster_target = st.number_input(
                    "Required completed respondents", min_value=1,
                    value=400, step=25, key="cluster_target_respondents",
                )
                cluster_size = st.number_input(
                    "Average respondents per cluster", min_value=1,
                    value=20, step=1, key="cluster_average_size",
                )
            with cluster_col2:
                cluster_icc = st.number_input(
                    "Intraclass correlation (ICC)", min_value=0.0,
                    max_value=1.0, value=0.05, step=0.01,
                    key="cluster_icc",
                )
                cluster_nonresponse = st.number_input(
                    "Cluster plan nonresponse rate", min_value=0.0,
                    max_value=0.99, value=0.10, step=0.01,
                    key="cluster_nonresponse",
                )
            if st.button("Plan clusters", key="run_cluster_sample_plan"):
                try:
                    result = run_cluster_sample_plan_service(
                        total_respondents=int(cluster_target),
                        average_cluster_size=int(cluster_size),
                        intraclass_correlation=cluster_icc,
                        nonresponse_rate=cluster_nonresponse,
                    )
                    st.session_state["cluster_sample_plan_result"] = result
                except (TypeError, ValueError, KeyError) as exc:
                    st.error(str(exc))
            cluster_result = st.session_state.get("cluster_sample_plan_result")
            if cluster_result is not None:
                st.dataframe(cluster_result.tables["cluster_plan"], hide_index=True, use_container_width=True)
                for warning in cluster_result.limitations:
                    st.warning(warning)

        with st.expander("Sampling selection and fieldwork list generator", expanded=False):
            from timan_intelligence.services.analysis_service import (
                run_sample_selection_service,
                run_stratified_sample_selection_service,
            )

            st.write(
                "Upload a complete sampling frame and select units reproducibly. "
                "Main and reserve samples are exported separately. PPSWOR here uses "
                "successive selection; its conditional draw probabilities are not "
                "exact first-order inclusion probabilities."
            )
            sampling_frame_file = st.file_uploader(
                "Sampling frame (CSV)", type=["csv"], key="selection_frame_upload"
            )
            if sampling_frame_file is not None:
                try:
                    selection_frame = pd.read_csv(sampling_frame_file)
                    if selection_frame.empty or len(selection_frame.columns) == 0:
                        st.error("The uploaded sampling frame is empty.")
                    else:
                        selection_id = st.selectbox(
                            "Unique sampling-unit identifier",
                            selection_frame.columns, key="selection_id_col",
                        )
                        selection_method = st.selectbox(
                            "Selection design",
                            ["srswor", "srswr", "systematic", "ppswr", "ppswor"],
                            format_func=lambda value: {
                                "srswor": "Simple random — without replacement",
                                "srswr": "Simple random — with replacement",
                                "systematic": "Systematic random sampling",
                                "ppswr": "PPS — with replacement",
                                "ppswor": "PPS — successive without replacement",
                            }[value],
                            key="selection_method",
                        )
                        selection_size_col = None
                        if selection_method.startswith("pps"):
                            selection_size_col = st.selectbox(
                                "Positive measure of size",
                                [col for col in selection_frame.columns if col != selection_id],
                                key="selection_size_col",
                            )
                        selection_n = st.number_input(
                            "Main sample size", min_value=1,
                            max_value=max(1, len(selection_frame)),
                            value=min(30, len(selection_frame)), step=1,
                            key="selection_sample_size",
                        )
                        selection_reserve_n = st.number_input(
                            "Separate reserve sample size", min_value=0,
                            max_value=max(0, len(selection_frame) - int(selection_n)),
                            value=0, step=1, key="selection_reserve_size",
                        )
                        selection_seed = st.number_input(
                            "Random seed (record this for reproducibility)",
                            min_value=0, value=2026, step=1,
                            key="selection_seed",
                        )
                        if st.button("Select sampling units", type="primary", key="run_sampling_selection"):
                            try:
                                selected_result = run_sample_selection_service(
                                    selection_frame, selection_id, int(selection_n),
                                    method=selection_method, seed=int(selection_seed),
                                    size_column=selection_size_col,
                                    reserve_size=int(selection_reserve_n),
                                )
                                st.session_state["sampling_selection_result"] = selected_result
                                st.session_state["sampling_selection_frame_name"] = sampling_frame_file.name
                            except (TypeError, ValueError, KeyError) as exc:
                                st.error(str(exc))
                        selected_result = st.session_state.get("sampling_selection_result")
                        if selected_result is not None:
                            st.metric("Main sample selected", f"{selected_result.metadata['sample_size']:,}")
                            st.dataframe(selected_result.tables["selected_sample"], hide_index=True, use_container_width=True)
                            st.download_button(
                                "Download main fieldwork list (CSV)",
                                data=selected_result.tables["selected_sample"].to_csv(index=False).encode("utf-8"),
                                file_name="timanstat_main_fieldwork_sample.csv",
                                mime="text/csv", key="download_main_fieldwork_sample",
                            )
                            if not selected_result.tables["reserve_sample"].empty:
                                st.dataframe(selected_result.tables["reserve_sample"], hide_index=True, use_container_width=True)
                                st.download_button(
                                    "Download reserve list (CSV)",
                                    data=selected_result.tables["reserve_sample"].to_csv(index=False).encode("utf-8"),
                                    file_name="timanstat_reserve_fieldwork_sample.csv",
                                    mime="text/csv", key="download_reserve_fieldwork_sample",
                                )
                            st.caption(
                                f"Method: {selected_result.method} | Seed: {selected_result.metadata['seed']} | "
                                f"Frame size: {selected_result.metadata['population_size']}"
                            )
                            for warning in selected_result.limitations:
                                st.warning(warning)
                except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as exc:
                    st.error(f"Could not read the sampling frame: {exc}")

        with st.expander("Survey weighting and adjustment engine", expanded=False):
            st.markdown(
                "Build analysis weights in a transparent sequence: inverse-probability "
                "base weights, nonresponse adjustment, population calibration, raking "
                "and optional trimming. The workflow preserves the original records."
            )
            st.caption(
                "Use exact first-order unit inclusion probabilities (πᵢ), not per-draw "
                "probabilities or conditional PPSWOR draw probabilities."
            )
            if df is not None:
                weighting_source = st.radio(
                    "Weighting data source",
                    ["Use the active dataset", "Upload a separate CSV"],
                    horizontal=True, key="weighting_data_source",
                )
            else:
                weighting_source = "Upload a separate CSV"
            weighting_frame = None
            if weighting_source == "Use the active dataset" and df is not None:
                weighting_frame = df.copy()
                st.caption(f"Using active dataset: {st.session_state.get('dataset_name', 'Loaded dataset')}")
            else:
                weighting_file = st.file_uploader(
                    "Sampled-unit dataset (CSV)",
                    type=["csv"], key="survey_weighting_upload",
                )
                if weighting_file is not None:
                    try:
                        weighting_frame = pd.read_csv(weighting_file)
                    except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as exc:
                        st.error(f"Could not read the weighting dataset: {exc}")
            if weighting_frame is not None:
                if weighting_frame.empty:
                    st.error("The weighting dataset is empty.")
                else:
                    numeric_weight_columns = list(
                        weighting_frame.select_dtypes(include="number").columns
                    )
                    if not numeric_weight_columns:
                        st.error("The dataset needs a numeric inclusion-probability column.")
                    else:
                        wleft, wright = st.columns(2)
                        with wleft:
                            weight_pi_col = st.selectbox(
                                "Exact first-order inclusion probability (πᵢ)",
                                numeric_weight_columns, key="weight_pi_col",
                                help="Each value must be in (0, 1]. This is not the same as a conditional probability at a PPSWOR draw.",
                            )
                        with wright:
                            use_nonresponse = st.checkbox(
                                "Adjust for nonresponse", value=False,
                                key="weight_use_nonresponse",
                            )
                        weight_response_col = None
                        weight_cells = []
                        if use_nonresponse:
                            response_candidates = [
                                column for column in numeric_weight_columns
                                if column != weight_pi_col
                            ]
                            if not response_candidates:
                                st.error("Add a numeric 0/1 response-indicator column before applying nonresponse adjustment.")
                            else:
                                weight_response_col = st.selectbox(
                                    "Response indicator (1 = respondent, 0 = nonrespondent)",
                                    response_candidates,
                                    key="weight_response_col",
                                )
                            weight_cells = st.multiselect(
                                "Nonresponse adjustment-cell variables",
                                [column for column in weighting_frame.columns if column not in {weight_pi_col, weight_response_col}],
                                key="weight_adjustment_cells",
                                help="Every adjustment cell must contain at least one respondent.",
                            )
                        controls_file = st.file_uploader(
                            "Population control totals (optional CSV)",
                            type=["csv"], key="weighting_controls_upload",
                            help="Required columns: variable, category, target_total. One row per category and variable.",
                        )
                        margin_data = None
                        if controls_file is not None:
                            try:
                                margin_data = pd.read_csv(controls_file)
                                required = {"variable", "category", "target_total"}
                                if not required.issubset(margin_data.columns):
                                    st.error("Control totals must contain variable, category and target_total columns.")
                                    margin_data = None
                                elif margin_data[["variable", "category", "target_total"]].isna().any().any():
                                    st.error("Control-total rows cannot contain missing values.")
                                    margin_data = None
                                else:
                                    margin_data["variable"] = margin_data["variable"].astype(str)
                                    margin_data["category"] = margin_data["category"].astype(str)
                                    margin_data["target_total"] = pd.to_numeric(margin_data["target_total"], errors="coerce")
                                    if not np.isfinite(margin_data["target_total"].to_numpy(dtype=float)).all() or (margin_data["target_total"] <= 0).any():
                                        st.error("Every population target must be positive and finite.")
                                        margin_data = None
                                    elif margin_data.duplicated(["variable", "category"]).any():
                                        st.error("Each variable/category combination must appear only once.")
                                        margin_data = None
                            except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as exc:
                                st.error(f"Could not read population controls: {exc}")
                                margin_data = None
                        poststrata_col = None
                        population_totals = None
                        raking_margins = None
                        analysis_frame = weighting_frame.copy()
                        if margin_data is not None:
                            available_margins = sorted(
                                set(margin_data["variable"]).intersection(set(map(str, weighting_frame.columns)))
                            )
                            if not available_margins:
                                st.error("No population-control variables match the dataset columns.")
                            else:
                                post_choice = st.selectbox(
                                    "Post-stratification variable (optional)",
                                    ["None"] + available_margins,
                                    key="weight_poststrata_col",
                                )
                                if post_choice != "None":
                                    poststrata_col = f"_timan_post_{post_choice}"
                                    analysis_frame[poststrata_col] = (
                                        weighting_frame[post_choice].astype("string").fillna("<MISSING>").astype(str)
                                    )
                                    control_rows = margin_data[margin_data["variable"] == post_choice]
                                    population_totals = dict(zip(
                                        control_rows["category"],
                                        control_rows["target_total"].astype(float),
                                    ))
                                rake_choices = st.multiselect(
                                    "Raking margins (optional)",
                                    available_margins,
                                    key="weight_raking_variables",
                                    help="Select multiple margins when their target totals refer to the same population and are mutually coherent.",
                                )
                                if rake_choices:
                                    raking_margins = {}
                                    for margin_variable in rake_choices:
                                        internal_column = f"_timan_rake_{margin_variable}"
                                        analysis_frame[internal_column] = (
                                            weighting_frame[margin_variable].astype("string").fillna("<MISSING>").astype(str)
                                        )
                                        control_rows = margin_data[margin_data["variable"] == margin_variable]
                                        raking_margins[internal_column] = dict(zip(
                                            control_rows["category"],
                                            control_rows["target_total"].astype(float),
                                        ))
                        use_trimming = st.checkbox(
                            "Trim extreme weights (winsorisation)", value=False,
                            key="weight_use_trimming",
                        )
                        trim_limits = None
                        if use_trimming:
                            trim_limits = st.slider(
                                "Lower and upper trimming quantiles",
                                min_value=0.0, max_value=1.0,
                                value=(0.01, 0.99), step=0.01,
                                key="weight_trim_quantiles",
                            )
                        if st.button(
                            "Construct and validate survey weights",
                            type="primary", key="run_survey_weighting",
                        ):
                            try:
                                if use_nonresponse and (weight_response_col is None or not weight_cells):
                                    raise ValueError("Select a valid numeric 0/1 response indicator and at least one nonresponse adjustment-cell variable.")
                                weighting_result = run_survey_weighting_service(
                                    analysis_frame,
                                    weight_pi_col,
                                    response_column=weight_response_col,
                                    adjustment_cells=weight_cells or None,
                                    poststrata_column=poststrata_col,
                                    population_totals=population_totals,
                                    raking_margins=raking_margins,
                                    trim_quantiles=trim_limits,
                                )
                                helper_columns = [
                                    column for column in weighting_result.tables["weighted_dataset"].columns
                                    if str(column).startswith("_timan_post_") or str(column).startswith("_timan_rake_")
                                ]
                                if helper_columns:
                                    weighting_result.tables["weighted_dataset"] = (
                                        weighting_result.tables["weighted_dataset"].drop(columns=helper_columns)
                                    )
                                st.session_state["survey_weighting_result"] = weighting_result
                                st.session_state["survey_weighting_dataset_key"] = _dataset_analysis_key(weighting_frame)
                            except (TypeError, ValueError, KeyError) as exc:
                                st.error(str(exc))
                        weighting_result = st.session_state.get("survey_weighting_result")
                        current_weighting_key = _dataset_analysis_key(weighting_frame)
                        if (
                            weighting_result is not None
                            and st.session_state.get("survey_weighting_dataset_key") == current_weighting_key
                        ):
                            st.markdown("#### Weight diagnostics")
                            diag = weighting_result.metadata.get("diagnostics", {})
                            metric_cols = st.columns(4)
                            metric_cols[0].metric("Records weighted", f"{diag.get('n', 0):,}")
                            metric_cols[1].metric("Kish effective n", f"{diag.get('kish_effective_sample_size', 0):,.1f}")
                            metric_cols[2].metric("Weight CV", f"{diag.get('coefficient_of_variation', 0):.3f}")
                            metric_cols[3].metric("Approx. unequal-weight DEFF", f"{diag.get('kish_deff_approximation', 0):.3f}")
                            st.dataframe(
                                weighting_result.tables["weight_diagnostics"],
                                hide_index=True, use_container_width=True,
                            )
                            st.caption(
                                "Kish effective sample size and unequal-weighting DEFF are approximations. "
                                "They do not account for the full variance effects of clustering, stratification or calibration."
                            )
                            st.markdown("**Weight construction stages**")
                            for stage in weighting_result.metadata.get("stages", []):
                                st.write(f"• {stage}")
                            st.dataframe(
                                weighting_result.tables["weighted_dataset"].head(100),
                                hide_index=True, use_container_width=True,
                            )
                            st.download_button(
                                "Download weighted dataset (CSV)",
                                data=weighting_result.tables["weighted_dataset"].to_csv(index=False).encode("utf-8-sig"),
                                file_name="timanstat_weighted_survey_dataset.csv",
                                mime="text/csv", key="download_weighted_survey_dataset",
                            )
                            st.download_button(
                                "Download weight diagnostics (CSV)",
                                data=weighting_result.tables["weight_diagnostics"].to_csv(index=False).encode("utf-8-sig"),
                                file_name="timanstat_weight_diagnostics.csv",
                                mime="text/csv", key="download_weight_diagnostics_existing",
                            )
                            st.markdown("#### Technical report")
                            report_col1, report_col2 = st.columns(2)
                            with report_col1:
                                report_project_name = st.text_input(
                                    "Project / study name (optional)",
                                    key="weight_report_project_name",
                                )
                            with report_col2:
                                report_prepared_by = st.text_input(
                                    "Prepared by (optional)",
                                    key="weight_report_prepared_by",
                                )
                            try:
                                weighting_pdf = generate_survey_weighting_pdf_report(
                                    weighting_result,
                                    project_name=report_project_name.strip() or None,
                                    prepared_by=report_prepared_by.strip() or None,
                                )
                                st.download_button(
                                    "Download survey weighting technical report (PDF)",
                                    data=weighting_pdf,
                                    file_name="TimanStat_Survey_Weighting_Technical_Report.pdf",
                                    mime="application/pdf",
                                    type="primary",
                                    key="download_survey_weighting_technical_report",
                                )
                            except (TypeError, ValueError, KeyError) as exc:
                                st.error(f"Could not generate the weighting technical report: {exc}")
                            for finding in weighting_result.findings:
                                st.success(finding)
                            for warning in weighting_result.limitations:
                                st.warning(warning)


        with st.expander("Survey estimation and inference engine", expanded=False):
            st.markdown(
                "Estimate population totals, weighted means and category proportions. "
                "Choose the sampling design so standard errors and confidence intervals "
                "match the available design information."
            )
            stored_weighting = st.session_state.get("survey_weighting_result")
            stored_weighting_key = st.session_state.get("survey_weighting_dataset_key")
            current_candidate_key = _dataset_analysis_key(weighting_frame) if weighting_frame is not None else None
            active_candidate_key = _dataset_analysis_key(df) if df is not None else None
            stored_weighted_frame = (
                stored_weighting.tables.get("weighted_dataset")
                if stored_weighting is not None and hasattr(stored_weighting, "tables")
                else None
            )
            weighted_result_is_current = (
                isinstance(stored_weighted_frame, pd.DataFrame)
                and stored_weighting_key is not None
                and stored_weighting_key in {current_candidate_key, active_candidate_key}
            )
            estimation_options = []
            if df is not None:
                estimation_options.append("Active dataset")
            if weighted_result_is_current:
                estimation_options.append("Previously weighted dataset")
            if not estimation_options:
                st.info("Load a dataset or construct survey weights above before running survey estimation.")
            else:
                default_source = "Previously weighted dataset" if weighted_result_is_current else "Active dataset"
                estimation_source = st.radio(
                    "Estimation data source", estimation_options,
                    index=estimation_options.index(default_source),
                    horizontal=True, key="survey_estimation_source",
                )
                if estimation_source == "Previously weighted dataset":
                    estimation_frame = stored_weighted_frame.copy()
                    default_weight = "analysis_weight"
                    st.caption("Using the final analysis weights produced by the weighting engine above.")
                else:
                    estimation_frame = df.copy()
                    default_weight = None
                numeric_estimation_columns = list(
                    estimation_frame.select_dtypes(include="number").columns
                )
                if not numeric_estimation_columns:
                    st.error("The selected dataset has no numeric columns for a survey weight.")
                else:
                    eleft, eright = st.columns(2)
                    with eleft:
                        estimand_label = st.selectbox(
                            "Population parameter",
                            ["Mean", "Total", "Category proportion"],
                            key="survey_estimation_estimand",
                        )
                        estimand = {
                            "Mean": "mean", "Total": "total",
                            "Category proportion": "proportion",
                        }[estimand_label]
                    with eright:
                        weight_default_index = (
                            numeric_estimation_columns.index(default_weight)
                            if default_weight in numeric_estimation_columns else 0
                        )
                        estimation_weight = st.selectbox(
                            "Final analysis weight", numeric_estimation_columns,
                            index=weight_default_index, key="survey_estimation_weight",
                        )
                    internal_weight_columns = {
                        "base_weight", "nonresponse_adjusted_weight",
                        "poststratified_weight", "raked_weight",
                        "trimmed_weight", "analysis_weight",
                    }
                    outcome_candidates = [
                        column for column in estimation_frame.columns
                        if column != estimation_weight
                        and column not in internal_weight_columns
                        and not str(column).startswith("_timan_")
                        and (
                            (estimand in {"mean", "total"} and pd.api.types.is_numeric_dtype(estimation_frame[column]))
                            or estimand == "proportion"
                        )
                    ]
                    if not outcome_candidates:
                        st.error("No suitable outcome variable is available for this estimand.")
                    else:
                        estimation_outcome = st.selectbox(
                            "Outcome variable", outcome_candidates,
                            key="survey_estimation_outcome",
                        )
                        design_label = st.selectbox(
                            "Sampling design",
                            [
                                "Weighted descriptive only (no design-based SE)",
                                "Stratified one-stage SRS (constant expansion weights)",
                                "One-stage PSU cluster sample (with-replacement variance)",
                            ],
                            key="survey_estimation_design",
                        )
                        design = {
                            "Weighted descriptive only (no design-based SE)": "weighted_descriptive",
                            "Stratified one-stage SRS (constant expansion weights)": "stratified_srs",
                            "One-stage PSU cluster sample (with-replacement variance)": "cluster_wr",
                        }[design_label]
                        strata_variable = None
                        cluster_variable = None
                        if design == "stratified_srs":
                            strata_candidates = [
                                column for column in estimation_frame.columns
                                if column not in {estimation_outcome, estimation_weight}
                            ]
                            if strata_candidates:
                                strata_variable = st.selectbox(
                                    "Stratum identifier", strata_candidates,
                                    key="survey_estimation_strata",
                                )
                            else:
                                st.error("A stratum identifier is required.")
                        elif design == "cluster_wr":
                            cluster_candidates = [
                                column for column in estimation_frame.columns
                                if column not in {estimation_outcome, estimation_weight}
                            ]
                            if cluster_candidates:
                                cluster_variable = st.selectbox(
                                    "Primary sampling unit (PSU)", cluster_candidates,
                                    key="survey_estimation_cluster",
                                )
                                optional_strata = ["No strata"] + [
                                    column for column in cluster_candidates
                                    if column != cluster_variable
                                ]
                                selected_strata = st.selectbox(
                                    "Stratification variable (optional)",
                                    optional_strata, key="survey_estimation_cluster_strata",
                                )
                                strata_variable = None if selected_strata == "No strata" else selected_strata
                            else:
                                st.error("A PSU identifier is required.")
                        confidence_level = st.select_slider(
                            "Confidence level", options=[0.90, 0.95, 0.99],
                            value=0.95, format_func=lambda value: f"{value:.0%}",
                            key="survey_estimation_confidence",
                        )
                        if st.button(
                            "Run survey estimation", type="primary",
                            key="run_survey_estimation",
                        ):
                            try:
                                estimation_result = run_survey_estimation_service(
                                    estimation_frame,
                                    estimation_outcome,
                                    estimation_weight,
                                    estimand=estimand,
                                    design=design,
                                    strata_variable=strata_variable,
                                    cluster_variable=cluster_variable,
                                    confidence_level=confidence_level,
                                )
                                st.session_state["survey_estimation_result"] = estimation_result
                                st.session_state["survey_estimation_result_key"] = (
                                    _dataset_analysis_key(estimation_frame),
                                    estimand, estimation_outcome, estimation_weight,
                                    design, strata_variable, cluster_variable,
                                    confidence_level,
                                )
                            except (TypeError, ValueError, KeyError) as exc:
                                st.error(f"Survey estimation could not be completed: {exc}")
                        expected_estimation_key = (
                            _dataset_analysis_key(estimation_frame),
                            estimand, estimation_outcome, estimation_weight,
                            design, strata_variable, cluster_variable,
                            confidence_level,
                        )
                        saved_estimation = st.session_state.get("survey_estimation_result")
                        if (
                            saved_estimation is not None
                            and st.session_state.get("survey_estimation_result_key") == expected_estimation_key
                        ):
                            st.markdown("#### Estimation results")
                            st.caption(f"Method: {saved_estimation.method}")
                            st.dataframe(
                                saved_estimation.tables["estimates"],
                                hide_index=True, use_container_width=True,
                            )
                            details_table = saved_estimation.tables.get("design_details")
                            if isinstance(details_table, pd.DataFrame) and not details_table.empty:
                                st.markdown("**Stratum / PSU variance details**")
                                st.dataframe(details_table, hide_index=True, use_container_width=True)
                            st.download_button(
                                "Download survey estimates (CSV)",
                                data=saved_estimation.tables["estimates"].to_csv(index=False).encode("utf-8-sig"),
                                file_name="TimanStat_Survey_Estimates.csv",
                                mime="text/csv", key="download_survey_estimates",
                            )
                            for finding in saved_estimation.findings:
                                st.success(finding)
                            for warning in saved_estimation.limitations:
                                st.warning(warning)
                            st.markdown("**Technical report**")
                            report_col1, report_col2 = st.columns(2)
                            with report_col1:
                                estimation_report_project = st.text_input(
                                    "Project / study name (optional)",
                                    key="estimation_report_project",
                                )
                            with report_col2:
                                estimation_report_preparer = st.text_input(
                                    "Prepared by (optional)",
                                    key="estimation_report_preparer",
                                )
                            try:
                                estimation_pdf = generate_survey_estimation_pdf_report(
                                    saved_estimation,
                                    project_name=estimation_report_project.strip() or None,
                                    prepared_by=estimation_report_preparer.strip() or None,
                                )
                                st.download_button(
                                    "Download survey estimation technical report (PDF)",
                                    data=estimation_pdf,
                                    file_name="TimanStat_Survey_Estimation_Technical_Report.pdf",
                                    mime="application/pdf",
                                    type="primary",
                                    key="download_survey_estimation_report",
                                )
                            except (TypeError, ValueError, KeyError) as exc:
                                st.error(f"Could not generate the estimation report: {exc}")

                st.markdown("#### Domain / subpopulation estimation")
                st.caption(
                    "Estimate totals, means or category proportions for a subgroup "
                    "while retaining every record in the original sample for variance estimation."
                )
                domain_candidates = [
                    column for column in estimation_frame.columns
                    if column not in {estimation_outcome, estimation_weight}
                    and not str(column).startswith("_timan_")
                ]
                if not domain_candidates:
                    st.info("A separate domain-identification variable is required.")
                else:
                    domain_variable = st.selectbox(
                        "Domain identifier", domain_candidates,
                        key="survey_domain_variable",
                    )
                    domain_values = estimation_frame[domain_variable].dropna().unique().tolist()
                    if not domain_values:
                        st.warning("The selected domain variable has no observed categories.")
                    else:
                        domain_value = st.selectbox(
                            "Target domain / category", domain_values,
                            format_func=str, key="survey_domain_value",
                        )
                        domain_estimand_label = st.selectbox(
                            "Domain parameter",
                            ["Mean", "Total", "Category proportion"],
                            key="survey_domain_estimand",
                        )
                        domain_estimand = {
                            "Mean": "mean", "Total": "total",
                            "Category proportion": "proportion",
                        }[domain_estimand_label]
                        if st.button(
                            "Run domain estimation", type="primary",
                            key="run_survey_domain_estimation",
                        ):
                            try:
                                domain_result = run_domain_survey_estimation_service(
                                    estimation_frame,
                                    estimation_outcome,
                                    estimation_weight,
                                    domain_variable,
                                    domain_value,
                                    estimand=domain_estimand,
                                    design=design,
                                    strata_variable=strata_variable,
                                    cluster_variable=cluster_variable,
                                    confidence_level=confidence_level,
                                )
                                st.session_state["survey_domain_estimation_result"] = domain_result
                                st.session_state["survey_domain_estimation_result_key"] = (
                                    _dataset_analysis_key(estimation_frame),
                                    estimation_outcome, estimation_weight, domain_variable,
                                    str(domain_value), domain_estimand, design,
                                    strata_variable, cluster_variable, confidence_level,
                                )
                            except (TypeError, ValueError, KeyError) as exc:
                                st.error(f"Domain estimation could not be completed: {exc}")
                        expected_domain_key = (
                            _dataset_analysis_key(estimation_frame),
                            estimation_outcome, estimation_weight, domain_variable,
                            str(domain_value), domain_estimand, design,
                            strata_variable, cluster_variable, confidence_level,
                        )
                        saved_domain = st.session_state.get("survey_domain_estimation_result")
                        if (
                            saved_domain is not None
                            and st.session_state.get("survey_domain_estimation_result_key") == expected_domain_key
                        ):
                            st.markdown("**Domain estimates**")
                            st.dataframe(
                                saved_domain.tables["estimates"],
                                hide_index=True, use_container_width=True,
                            )
                            domain_details = saved_domain.tables.get("design_details")
                            if isinstance(domain_details, pd.DataFrame) and not domain_details.empty:
                                st.markdown("**Full-sample design variance details**")
                                st.dataframe(domain_details, hide_index=True, use_container_width=True)
                            st.download_button(
                                "Download domain estimates (CSV)",
                                data=saved_domain.tables["estimates"].to_csv(index=False).encode("utf-8-sig"),
                                file_name="TimanStat_Survey_Domain_Estimates.csv",
                                mime="text/csv", key="download_survey_domain_estimates",
                            )
                            for finding in saved_domain.findings:
                                st.success(finding)
                            for warning in saved_domain.limitations:
                                st.warning(warning)
                            st.markdown("**Domain technical report**")
                            domain_report_col1, domain_report_col2 = st.columns(2)
                            with domain_report_col1:
                                domain_report_project = st.text_input(
                                    "Domain report project / study name (optional)",
                                    key="domain_estimation_report_project",
                                )
                            with domain_report_col2:
                                domain_report_preparer = st.text_input(
                                    "Domain report prepared by (optional)",
                                    key="domain_estimation_report_preparer",
                                )
                            try:
                                domain_pdf = generate_survey_estimation_pdf_report(
                                    saved_domain,
                                    report_title="Survey Domain and Subpopulation Estimation Report",
                                    project_name=domain_report_project.strip() or None,
                                    prepared_by=domain_report_preparer.strip() or None,
                                )
                                st.download_button(
                                    "Download domain estimation technical report (PDF)",
                                    data=domain_pdf,
                                    file_name="TimanStat_Survey_Domain_Estimation_Report.pdf",
                                    mime="application/pdf",
                                    type="primary",
                                    key="download_survey_domain_estimation_report",
                                )
                            except (TypeError, ValueError, KeyError) as exc:
                                st.error(f"Could not generate the domain estimation report: {exc}")

        st.info(
            "Unweighted question-level frequencies above describe the imported "
            "records. Use the weighted estimator separately when a documented "
            "survey weight is available. Two-stage design-based totals, means "
            "and proportions are available when their sampling-frame counts and "
            "SSU-level aggregates are supplied; other complex designs remain "
            "unsupported."
        )
    else:
        st.info("Upload and import a survey dataset in Data Management to begin.")


# ============================================================
# STATISTICAL INFERENCE
# ============================================================

elif page == "Statistical Inference":
    st.markdown(
        """
        <section class="analysis-page-header">
            <div class="analysis-page-eyebrow">STATISTICAL WORKSPACE · MODULE 02</div>
            <div class="analysis-page-title">Statistical Inference</div>
            <div class="analysis-page-description">
                Move beyond describing the observed data to estimate population
                parameters, quantify uncertainty and evaluate statistical evidence.
                Analysis methods will be made available here as they are validated.
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.caption(status_text(MODULES[page][0]))
    st.markdown(
        """
        <div class="analysis-workflow">
            <div><strong>01</strong><b>Prepare</b><small>Check variables and design</small></div>
            <div><strong>02</strong><b>Specify</b><small>State hypotheses</small></div>
            <div><strong>03</strong><b>Estimate</b><small>Quantify uncertainty</small></div>
            <div><strong>04</strong><b>Interpret</b><small>Assess evidence</small></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    inference_df = get_dataset()
    if inference_df is None:
        st.info(
            "Load a dataset in Data Management to prepare for inferential analysis."
        )
        st.button(
            "Open Data Management",
            key="inference_open_data_management",
            type="primary",
            on_click=navigate_to,
            args=("Data Management",),
        )
    else:
        numeric_count = len(
            inference_df.select_dtypes(include="number").columns
        )
        categorical_count = len(inference_df.columns) - numeric_count
        missing_count = int(inference_df.isna().sum().sum())
        total_count = int(inference_df.shape[0] * inference_df.shape[1])
        completeness = (
            (total_count - missing_count) / total_count * 100
            if total_count else 0.0
        )
        st.markdown("#### Dataset readiness")
        st.caption(
            f"Active dataset · {len(inference_df):,} records · "
            f"{len(inference_df.columns):,} variables"
        )
        readiness = st.columns(4)
        readiness[0].metric("Records", f"{len(inference_df):,}")
        readiness[1].metric("Numeric variables", f"{numeric_count:,}")
        readiness[2].metric("Other variables", f"{categorical_count:,}")
        readiness[3].metric("Completeness", f"{completeness:.1f}%")
        with st.expander("Review variables available for future inference", expanded=False):
            variable_inventory = pd.DataFrame(
                {
                    "Variable": [str(column) for column in inference_df.columns],
                    "Data type": [str(inference_df[column].dtype) for column in inference_df.columns],
                    "Observed values": [int(inference_df[column].notna().sum()) for column in inference_df.columns],
                    "Missing values": [int(inference_df[column].isna().sum()) for column in inference_df.columns],
                    "Distinct values": [int(inference_df[column].nunique(dropna=True)) for column in inference_df.columns],
                }
            )
            st.dataframe(
                variable_inventory,
                hide_index=True,
                use_container_width=True,
            )

    st.markdown("#### Planned inference capabilities")
    inference_cards = [
        (
            "Estimation and confidence intervals",
            "Estimate means, proportions and differences with uncertainty intervals.",
            "Parameter estimation",
        ),
        (
            "Hypothesis testing",
            "Evaluate pre-specified hypotheses using suitable test assumptions and effect sizes.",
            "Statistical tests",
        ),
        (
            "Association and group comparisons",
            "Assess relationships and differences between independent or paired groups.",
            "Comparative inference",
        ),
        (
            "Assumption diagnostics",
            "Check distributional, independence and variance assumptions before interpreting results.",
            "Model diagnostics",
        ),
    ]
    for card_start in range(0, len(inference_cards), 2):
        card_columns = st.columns(2)
        for offset, card in enumerate(inference_cards[card_start:card_start + 2]):
            with card_columns[offset]:
                st.markdown(
                    f"""
                    <div class="feature-card">
                        <div class="feature-number">{card[2].upper()}</div>
                        <div class="feature-title">{card[0]}</div>
                        <div class="feature-description">{card[1]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.info(
        "This workspace is currently an interface and preparation view. "
        "Inferential calculations are not enabled here yet. Methods will be "
        "released only after validation of assumptions, statistical outputs "
        "and interpretation safeguards."
    )
    st.button(
        "Open Descriptive Statistics",
        key="inference_open_descriptive",
        on_click=navigate_to,
        args=("Descriptive Statistics",),
    )


# ============================================================
# DESCRIPTIVE STATISTICS
# ============================================================

elif page == "Descriptive Statistics":
    st.markdown(
        """
        <div class="analysis-page-header">
            <div class="analysis-page-eyebrow">STATISTICAL WORKSPACE · MODULE 01</div>
            <div class="analysis-page-title">Descriptive Statistics</div>
            <div class="analysis-page-description">
                Summarise your dataset, understand distributions and compare
                groups before moving to inferential analysis.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(status_text(MODULES[page][0]))

    df = get_dataset()

    if df is not None:
        numeric_cols = list(df.select_dtypes(include="number").columns)
        categorical_cols = [
            col for col in df.columns
            if not pd.api.types.is_numeric_dtype(df[col].dtype)
        ]
        st.markdown("#### Analysis readiness")
        ready_columns = st.columns(4, gap="medium")
        ready_columns[0].metric("Records", f"{len(df):,}")
        ready_columns[1].metric("Variables", f"{df.shape[1]:,}")
        ready_columns[2].metric("Numeric", f"{len(numeric_cols):,}")
        ready_columns[3].metric("Categorical / other", f"{len(categorical_cols):,}")
        st.caption(
            f"Active dataset: **{st.session_state.get('dataset_name') or 'Uploaded dataset'}**. "
            "Variable types are based on how values were imported."
        )
        with st.expander("Inspect variables before analysis", expanded=False):
            variable_inventory = pd.DataFrame({
                "Variable": [str(col) for col in df.columns],
                "Imported type": [str(dtype) for dtype in df.dtypes],
                "Valid values": [int(df[col].notna().sum()) for col in df.columns],
                "Missing values": [int(df[col].isna().sum()) for col in df.columns],
                "Distinct values": [int(df[col].nunique(dropna=True)) for col in df.columns],
            })
            st.dataframe(variable_inventory, hide_index=True, use_container_width=True)

        st.markdown("#### Analysis workflow")
        st.markdown(
            """
            <div class="analysis-workflow">
                <div><span>1</span><strong>Review</strong><small>Check dataset structure</small></div>
                <div><span>2</span><strong>Calculate</strong><small>Generate descriptive results</small></div>
                <div><span>3</span><strong>Explore</strong><small>Inspect variables and patterns</small></div>
                <div><span>4</span><strong>Export</strong><small>Download selected outputs</small></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
            st.divider()
            st.markdown("#### Additional statistical methods")
            st.caption(
                "Choose an additional method only after confirming the outcome "
                "type, study design and relevant assumptions."
            )
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
    else:
        st.info("Upload a dataset to begin descriptive analysis.")
        st.button(
            "Go to Data Management",
            type="primary",
            key="descriptive_upload_dataset",
            on_click=go_to_data_management,
        )
# VISUALISATIONS
# ============================================================

elif page == "Visualisations":
    st.markdown(
        """
        <section class="analysis-page-header">
            <div class="analysis-page-eyebrow">VISUAL ANALYTICS · WORKSPACE 04</div>
            <div class="analysis-page-title">Data Visualisations</div>
            <div class="analysis-page-description">
                Build clear exploratory charts from your active dataset.
                Select a chart, choose the relevant variables and review
                what the visual does—and does not—represent.
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.caption(status_text(MODULES[page][0]))
    st.markdown(
        """
        <div class="analysis-workflow">
            <div><strong>01</strong><b>Select</b><small>Chart type</small></div>
            <div><strong>02</strong><b>Configure</b><small>Choose variables</small></div>
            <div><strong>03</strong><b>Explore</b><small>Review the pattern</small></div>
            <div><strong>04</strong><b>Interpret</b><small>Check context</small></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df = get_dataset()

    if df is not None:
        numeric_cols = list(
            df.select_dtypes(include="number").columns
        )
        all_cols = list(df.columns)
        categorical_count = len(all_cols) - len(numeric_cols)

        st.markdown("#### Dataset visualisation readiness")
        readiness = st.columns(4)
        readiness[0].metric("Records", f"{len(df):,}")
        readiness[1].metric("Variables", f"{len(all_cols):,}")
        readiness[2].metric("Numeric variables", f"{len(numeric_cols):,}")
        readiness[3].metric("Other variables", f"{categorical_count:,}")
        st.divider()
        st.markdown("#### Chart builder")

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
    else:
        st.info(
            "No dataset is loaded. Upload a dataset in Data Management "
            "to start building visualisations."
        )
        if st.button(
            "Go to Data Management",
            type="primary",
            key="visualisations_upload_dataset",
            on_click=go_to_data_management,
        ):
            pass


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