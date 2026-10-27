from pathlib import Path

code = '''import pandas as pd
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
    c.metric("AI Analyst", "Planned")
    if st.session_state.dataset is not None:
        df = st.session_state.dataset
        x, y, z = st.columns(3)
        x.metric("Rows", f"{len(df):,}")
        y.metric("Columns", f"{len(df.columns):,}")
        z.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
    else:
        st.info("Start in **Data Management** to upload a CSV or Excel dataset.")
    st.subheader("Platform modules")
    names = [n for n in MODULES if n not in ("Home", "About")]
    for start in range(0, len(names), 3):
        cols = st.columns(3)
        for col, name in zip(cols, names[start:start+3]):
            status, desc = MODULES[name]
            col.markdown(f'<div class="module-card"><h4>{name}</h4><b>{status_text(status)}</b><p>{desc}</p></div>', unsafe_allow_html=True)
    st.caption("Prototype notice: complex survey design, inferential procedures, causal analysis and AI question answering are not yet complete workflows.")

elif page == "Data Management":
    module_intro(page, "Upload a dataset, inspect its structure and preview records.", MODULES[page][0], [
        "Upload CSV and Excel (.xlsx) files.", "Inspect row and column counts and preview records.",
        "Review variable types, missing values and unique-value counts.",
        "Keep the source dataset unchanged during these initial checks."
    ])
    uploaded = st.file_uploader("Choose a CSV or Excel file", type=["csv", "xlsx"], help="Only upload data you are authorised to use. Do not upload confidential or identifiable data to this public prototype without appropriate safeguards.")
    if uploaded is not None:
        try:
            new_df = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
            st.session_state.dataset = new_df
            st.session_state.dataset_name = uploaded.name
            st.success(f"Dataset loaded: {uploaded.name}")
        except Exception as exc:
            st.error("Could not read the file. Check that it is a valid CSV or Excel file and that the Excel reader dependency is installed.")
            st.caption(f"Technical detail: {exc}")
    df = st.session_state.dataset
    if df is not None:
        a, b, c, d = st.columns(4)
        a.metric("Rows", f"{df.shape[0]:,}")
        b.metric("Columns", f"{df.shape[1]:,}")
        c.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
        d.metric("Duplicate rows", f"{int(df.duplicated().sum()):,}")
        st.subheader("Data preview")
        st.dataframe(df.head(100), use_container_width=True)
        st.subheader("Variable information")
        info = pd.DataFrame({"Variable": df.columns.astype(str), "Data type": [str(x) for x in df.dtypes], "Missing values": df.isna().sum().values, "Unique values": df.nunique(dropna=True).values})
        st.dataframe(info, use_container_width=True)
    else:
        st.info("Upload a CSV or Excel file to begin.")

elif page == "Data Quality":
    module_intro(page, "Review basic structural and completeness checks before interpreting results.", MODULES[page][0], [
        "Count missing cells by variable.", "Identify fully duplicated rows.",
        "Review data types and distinct-value counts.", "Export a quality profile for review."
    ])
    df = current_data()
    if df is not None:
        missing = df.isna().sum()
        quality = pd.DataFrame({"Variable": df.columns.astype(str), "Data type": [str(x) for x in df.dtypes], "Missing count": missing.values, "Missing percent": [(n / len(df) * 100) for n in missing.values], "Unique non-missing values": df.nunique(dropna=True).values})
        a, b, c = st.columns(3)
        a.metric("Records", f"{len(df):,}")
        b.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
        c.metric("Duplicate rows", f"{int(df.duplicated().sum()):,}")
        st.dataframe(quality, use_container_width=True)
        st.download_button("Download data-quality profile", quality.to_csv(index=False).encode("utf-8"), "timan_data_quality_profile.csv", "text/csv")
        st.warning("These checks flag potential issues; they do not automatically clean, impute, recode or remove records.")

elif page == "Descriptive Statistics":
    module_intro(page, "Summarise observed data and inspect distributions. Results describe the uploaded records.", MODULES[page][0], [
        "Numeric summaries such as mean, standard deviation, minimum and maximum.",
        "Frequency counts and percentages, including an explicit missing category.",
        "Cross-tabulations for two variables.", "Download selected descriptive outputs."
    ])
    df = current_data()
    if df is not None:
        st.subheader("Numeric summary")
        numeric = df.select_dtypes(include="number")
        if not numeric.empty:
            summary = numeric.describe().T
            st.dataframe(summary, use_container_width=True)
            st.download_button("Download numeric summary", summary.to_csv().encode("utf-8"), "timan_numeric_summary.csv", "text/csv")
        else:
            st.warning("No numeric variables were detected.")
        st.subheader("Frequency distribution")
        variable = st.selectbox("Select a variable", df.columns, key="desc_frequency")
        freq = df[variable].astype("string").fillna("(Missing)").value_counts(dropna=False).rename_axis("Category").reset_index(name="Frequency")
        freq["Percentage of all records"] = freq["Frequency"] / len(df) * 100 if len(df) else 0
        st.dataframe(freq, use_container_width=True)
        st.caption("Percentages use all records as the denominator, including missing values shown as '(Missing)'.")
        st.download_button("Download frequency table", freq.to_csv(index=False).encode("utf-8"), "timan_frequency_table.csv", "text/csv")
        if len(df.columns) >= 2:
            st.subheader("Cross-tabulation")
            left, right = st.columns(2)
            with left:
                row_var = st.selectbox("Rows", df.columns, key="cross_rows")
            with right:
                col_var = st.selectbox("Columns", df.columns, index=1, key="cross_cols")
            if row_var != col_var:
                tab = pd.crosstab(df[row_var].fillna("(Missing)"), df[col_var].fillna("(Missing)"), margins=True)
                st.dataframe(tab, use_container_width=True)
                st.download_button("Download cross-tabulation", tab.to_csv().encode("utf-8"), "timan_crosstab.csv", "text/csv")
            else:
                st.warning("Choose two different variables.")

elif page == "Visualisations":
    module_intro(page, "Create basic charts from the currently loaded dataset.", MODULES[page][0], [
        "Bar charts for category counts.", "Histograms for numeric distributions.",
        "Line charts for ordered numeric observations.", "Scatter plots for two numeric variables."
    ])
    df = current_data()
    if df is not None:
        chart = st.selectbox("Chart type", ["Bar chart", "Histogram", "Line chart", "Scatter plot"])
        numeric_cols = list(df.select_dtypes(include="number").columns)
        if chart == "Bar chart":
            var = st.selectbox("Variable", df.columns, key="bar_var")
            st.bar_chart(df[var].astype("string").fillna("(Missing)").value_counts())
        elif chart == "Histogram":
            if numeric_cols:
                var = st.selectbox("Numeric variable", numeric_cols, key="hist_var")
                values = pd.to_numeric(df[var], errors="coerce").dropna()
                if values.empty:
                    st.warning("No usable numeric values.")
                elif values.nunique() == 1:
                    st.bar_chart(values.value_counts().sort_index())
                else:
                    st.bar_chart(pd.cut(values, bins=min(10, max(2, values.nunique()))).value_counts().sort_index())
            else:
                st.warning("No numeric variables are available.")
        elif chart == "Line chart":
            if numeric_cols:
                var = st.selectbox("Numeric variable", numeric_cols, key="line_var")
                st.line_chart(pd.to_numeric(df[var], errors="coerce").dropna())
                st.caption("The chart follows current row order. Sort by a time variable before interpreting it as a time trend.")
            else:
                st.warning("No numeric variables are available.")
        else:
            if len(numeric_cols) >= 2:
                x = st.selectbox("X-axis", numeric_cols, key="scatter_x")
                y = st.selectbox("Y-axis", numeric_cols, index=1, key="scatter_y")
                if x == y:
                    st.warning("Choose two different variables.")
                else:
                    st.scatter_chart(df[[x, y]].apply(pd.to_numeric, errors="coerce").dropna(), x=x, y=y)
            else:
                st.warning("At least two numeric variables are needed.")

elif page == "Reports & Exports":
    module_intro(page, "Export source data and selected descriptive outputs for further use.", MODULES[page][0], [
        "Download the current dataset as CSV.", "Export descriptive statistics.",
        "Export a data-quality profile.", "Add reproducible narrative reports in a later phase."
    ])
    df = st.session_state.dataset
    if df is None:
        st.info("Upload a dataset first in Data Management.")
    else:
        st.download_button("Download dataset as CSV", df.to_csv(index=False).encode("utf-8"), "timan_data_export.csv", "text/csv")
        st.download_button("Download descriptive statistics as CSV", df.describe(include="all").T.to_csv().encode("utf-8"), "timan_descriptive_statistics.csv", "text/csv")
        missing = df.isna().sum()
        quality = pd.DataFrame({"Variable": df.columns.astype(str), "Data type": [str(x) for x in df.dtypes], "Missing count": missing.values, "Missing percent": [(n / len(df) * 100) if len(df) else 0 for n in missing.values], "Unique non-missing values": df.nunique(dropna=True).values})
        st.download_button("Download data-quality profile", quality.to_csv(index=False).encode("utf-8"), "timan_data_quality_profile.csv", "text/csv")
        st.caption("These are data exports, not a complete narrative analytical report.")

elif page == "Survey Analysis":
    module_intro(page, "A planned workflow for household surveys, needs assessments, feedback surveys and research questionnaires.", MODULES[page][0], [
        "Map questionnaire variables and response options.", "Analyse single- and multiple-response questions.",
        "Report denominators, non-response and missingness transparently.",
        "Support sampling weights, strata and clusters when implemented.",
        "Produce disaggregated tables and exportable survey outputs."
    ])
    st.caption("Complex survey estimation and design-adjusted standard errors are not yet available.")

elif page == "Statistical Inference":
    module_intro(page, "A planned module for inference beyond describing the observed dataset.", MODULES[page][0], [
        "Confidence intervals and uncertainty estimates.", "Hypothesis tests with explicit assumptions and effect sizes.",
        "Association analysis and regression diagnostics.",
        "Distinguish association from causal inference.",
        "Support design-adjusted inference when survey weights, strata and clusters are available."
    ])
    st.caption("No inferential tests are run here yet. Descriptive summaries should not be interpreted as tests of statistical significance.")

elif page == "Research & Modelling":
    module_intro(page, "A planned workspace for applied research and statistical modelling.", MODULES[page][0], [
        "Structure research questions, outcomes and explanatory variables.",
        "Support regression and other appropriate statistical models.",
        "Inspect model assumptions and diagnostics.",
        "Report effect estimates, uncertainty and limitations.",
        "Keep methods and transformations traceable."
    ])

elif page == "MEAL Intelligence":
    module_intro(page, "A planned workflow for Monitoring, Evaluation, Accountability and Learning teams.", MODULES[page][0], [
        "Organise indicators, definitions, baselines, targets and actual values.",
        "Track outputs, outcomes and disaggregated reach.",
        "Review indicator completeness and data-quality issues.",
        "Support results frameworks, evaluation questions and learning logs.",
        "Summarise feedback data without exposing personal records."
    ])

elif page == "Business Intelligence":
    module_intro(page, "A planned workflow for small businesses, enterprises and operational teams.", MODULES[page][0], [
        "Track sales, expenses, margins and cash-flow indicators.",
        "Compare performance across products, branches and time periods.",
        "Identify trends and unusual movements for review.",
        "Build KPI summaries and management reports.",
        "Support scenario comparisons with explicit assumptions."
    ])

elif page == "Forecasting & Prediction":
    module_intro(page, "A planned workspace for forecasting future values and building predictive models.", MODULES[page][0], [
        "Check time-index quality and available history.",
        "Compare forecasts with simple baselines.",
        "Evaluate out-of-sample prediction error.",
        "Display prediction uncertainty and limitations.",
        "Avoid causal claims from predictive performance alone."
    ])

elif page == "Optimisation & Scenarios":
    module_intro(page, "A planned workspace for exploring decisions under stated constraints and assumptions.", MODULES[page][0], [
        "Compare alternative assumptions and scenarios.",
        "Run sensitivity analysis on key inputs.",
        "Explore resource allocation against explicit constraints.",
        "Document objectives, assumptions and trade-offs.",
        "Export scenario comparisons for decision-makers."
    ])

elif page == "AI Analyst":
    module_intro(page, "The planned AI assistant will translate analytical questions into explicit, reviewable analysis steps.", MODULES[page][0], [
        "Interpret natural-language questions about a loaded dataset.",
        "Ask clarifying questions when variables or denominators are ambiguous.",
        "Call approved statistical functions rather than execute arbitrary generated code.",
        "Explain methods, sample sizes, assumptions and limitations.",
        "Ground follow-up questions in computed results."
    ])
    st.text_area("Example analytical question", placeholder="For example: Which ward has the highest reported household count?", disabled=True)
    st.caption("AI question answering is not connected; this page does not generate analytical answers.")

elif page == "Settings & Governance":
    module_intro(page, "A planned control area for responsible use of client data and reproducible analysis.", MODULES[page][0], [
        "User authentication and role-based permissions.",
        "Client and project separation with tenant isolation.",
        "Audit trails for uploads, transformations and analyses.",
        "Data-retention controls and secure handling of sensitive records.",
        "Analysis metadata, versioning and reproducibility."
    ])
    st.warning("The current prototype does not provide user accounts, tenant isolation or production-grade security. Do not use this public prototype for confidential or identifiable client datasets.")

elif page == "About":
    st.title("About Timan Intelligence")
    st.write("Timan Intelligence is a developing statistical analytics platform by Timan Analytics, intended for NGOs and MEAL teams, researchers, and businesses.")
    st.subheader("Platform principles")
    st.markdown("- **Statistical integrity:** use methods appropriate to the question and data.\\n- **Transparency:** disclose denominators, assumptions, missingness and limitations.\\n- **Reproducibility:** keep methods and transformations traceable.\\n- **Responsible AI:** validated functions perform calculations.\\n- **Privacy:** protect sensitive data before onboarding real clients.")
    st.divider()
    st.caption("Turning Data into Insights for Informed Decisions.")
'''

path = Path("/mnt/data/timan_intelligence_app.py")
path.write_text(code, encoding="utf-8")
print(f"Created revised app.py at {path} ({len(code.splitlines())} lines).")
