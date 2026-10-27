import io
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="TimanStat", page_icon="📊", layout="wide")

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
    "About": ("Available", "Learn about TimanStat and its current limitations."),
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

        unsafe_allow_html=True,
    )
    st.write("")
    st.write(
        "A statistical analytics platform for exploring datasets, checking data quality, "
        "calculating descriptive statistics and creating basic visualisations."
    )

    df = st.session_state.dataset
    if df is None:
        a, b, c = st.columns(3)
        a.metric("Dataset status", "Not loaded")
        b.metric("Available formats", "CSV / Excel")
        c.metric("Navigation modules", len(MODULES))
        st.info("To begin, select **Data Management** from the left navigation and upload a CSV or Excel file.")
        if st.button("Go to Data Management", type="primary"):
            st.session_state.navigation_page = "Data Management"
            st.rerun()
    else:
        a, b, c = st.columns(3)
        a.metric("Rows", f"{df.shape[0]:,}")
        b.metric("Columns", f"{df.shape[1]:,}")
        c.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
        st.subheader("Dataset preview")
        st.dataframe(df.head(10), use_container_width=True)
        st.caption(f"Current dataset: {st.session_state.dataset_name or 'Uploaded dataset'}")

    st.subheader("Module availability")
    status_rows = [
        {"Module": name, "Status": status, "Purpose": purpose}
        for name, (status, purpose) in MODULES.items()
    ]
    st.dataframe(pd.DataFrame(status_rows), hide_index=True, use_container_width=True)

# DATA MANAGEMENT
elif page == "Data Management":
    st.title("Data Management")
    st.caption(status_text(MODULES[page][0]))
    st.write("Upload a CSV or Excel workbook (.xlsx). The imported dataset stays available while you navigate this session.")

    uploaded_file = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx"],
        key="dataset_uploader",
        help="Supported formats: .csv and .xlsx. Password-protected workbooks are not supported.",
    )

    if uploaded_file is not None:
        current_name = st.session_state.get("dataset_name")
        # Avoid re-reading the same upload on every Streamlit rerun.
        if current_name != uploaded_file.name or st.session_state.dataset is None:
            try:
                imported = load_uploaded_file(uploaded_file)
                st.session_state.dataset = imported
                st.session_state.dataset_name = uploaded_file.name
                st.success(f"Successfully imported **{uploaded_file.name}**.")
            except Exception as exc:
                st.error(f"Import failed: {exc}")
        else:
            st.success(f"Dataset loaded: **{uploaded_file.name}**")

    df = st.session_state.dataset
    if df is not None:
        st.subheader("Imported dataset")
        a, b, c = st.columns(3)
        a.metric("Rows", f"{df.shape[0]:,}")
        b.metric("Columns", f"{df.shape[1]:,}")
        c.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
        st.dataframe(df.head(100), use_container_width=True)
        with st.expander("Column details"):
            details = pd.DataFrame({
                "Column": df.columns.astype(str),
                "Data type": [str(dtype) for dtype in df.dtypes],
                "Missing values": [int(value) for value in df.isna().sum().values],
                "Unique values": [int(df[col].nunique(dropna=True)) for col in df.columns],
            })
            st.dataframe(details, hide_index=True, use_container_width=True)
        st.download_button(
            "Download current dataset as CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_dataset_export.csv",
            mime="text/csv",
            key="download_dataset_management",
        )
    else:
        st.info("No dataset loaded yet. Choose a file above to get started.")

# DATA QUALITY
elif page == "Data Quality":
    st.title("Data Quality")
            frequencies = counts.rename_axis("Category").reset_index(name="Frequency")
            frequencies["Percentage (%)"] = (
                frequencies["Frequency"] / denominator * 100
            ).round(2) if denominator else 0.0
            st.dataframe(frequencies, hide_index=True, use_container_width=True)
            st.caption(
                f"Percentage denominator: {denominator:,} records"
                + (" (including missing values)." if include_missing else " (non-missing records only).")
            )
            st.download_button(
                "Download frequency table",
                data=frequencies.to_csv(index=False).encode("utf-8-sig"),
                file_name="timan_frequency_table.csv",
                mime="text/csv",
                key="download_frequency_table",
            )
        else:
            st.info("No non-numeric columns were detected for categorical frequency tables.")

# VISUALISATIONS
elif page == "Visualisations":
    st.title("Visualisations")
    st.caption(status_text(MODULES[page][0]))
    df = get_dataset()
    if df is not None:
        numeric_cols = list(df.select_dtypes(include="number").columns)
        all_cols = list(df.columns)
        chart_type = st.selectbox(
            "Chart type",
            ["Bar chart", "Histogram", "Line chart", "Scatter plot"],
        )

        if chart_type == "Bar chart":
            if not all_cols:
                st.info("No columns are available to chart.")
            else:
                col = st.selectbox("Category or value column", all_cols, key="bar_col")
                top_n = st.slider("Number of categories to show", min_value=3, max_value=30, value=10)
                counts = df[col].astype("object").where(df[col].notna(), "(Missing)").value_counts().head(top_n)
                st.bar_chart(counts)
                st.caption(f"Showing up to {top_n} most frequent values for {col}.")
        elif chart_type == "Histogram":
            if not numeric_cols:
                st.info("A histogram requires at least one numeric column.")
            else:
                col = st.selectbox("Numeric variable", numeric_cols, key="hist_col")
                bins = st.slider("Number of bins", min_value=5, max_value=50, value=20)
                values = pd.to_numeric(df[col], errors="coerce").dropna()
                if values.empty:
                    st.warning("This column has no usable numeric values.")
                else:
                    hist, edges = __import__("numpy").histogram(values, bins=bins)
                    chart_df = pd.DataFrame({
                        "Bin range": [
                            f"{edges[i]:.3g}–{edges[i + 1]:.3g}" for i in range(len(hist))
                        ],
                        "Frequency": hist,
                    }).set_index("Bin range")
                    st.bar_chart(chart_df)
        elif chart_type == "Line chart":
            if not numeric_cols:
                st.info("A line chart requires at least one numeric column.")
            else:
                col = st.selectbox("Numeric variable", numeric_cols, key="line_col")
                st.line_chart(pd.to_numeric(df[col], errors="coerce").reset_index(drop=True))
                st.caption("Points follow the dataset's current row order; no time variable is inferred.")
        elif chart_type == "Scatter plot":
            if len(numeric_cols) < 2:
                st.info("A scatter plot requires at least two numeric columns.")
            else:
                x_col = st.selectbox("X-axis variable", numeric_cols, key="scatter_x")
                y_options = [col for col in numeric_cols if col != x_col]
                y_col = st.selectbox("Y-axis variable", y_options, key="scatter_y")
                plot_df = df[[x_col, y_col]].apply(pd.to_numeric, errors="coerce").dropna()
                if plot_df.empty:
                    st.warning("The selected variables have no paired numeric observations.")
                else:
                    st.scatter_chart(plot_df, x=x_col, y=y_col)

# REPORTS & EXPORTS
elif page == "Reports & Exports":
    st.title("Reports & Exports")
    st.caption(status_text(MODULES[page][0]))
    df = get_dataset()
    if df is not None:
        st.write("Download the currently loaded data or available descriptive outputs.")
        st.download_button(
            "Download current dataset as CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_dataset_export.csv",
            mime="text/csv",
            key="download_dataset_reports",
        )
        summary = numeric_summary(df)
        st.download_button(
            "Download numeric descriptive statistics",
            data=summary.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_descriptive_statistics.csv",
            mime="text/csv",
            key="download_summary_reports",
        )
        quality = pd.DataFrame({
            "Variable": df.columns.astype(str),
            "Data type": [str(dtype) for dtype in df.dtypes],
            "Missing values": [int(value) for value in df.isna().sum().values],
            "Unique values": [int(df[col].nunique(dropna=True)) for col in df.columns],
        })
        st.download_button(
            "Download data-quality profile",
            data=quality.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_data_quality.csv",
            mime="text/csv",
            key="download_quality_reports",
        )
        st.info("Automated narrative report generation is under development.")
    else:
        st.info("Upload a dataset in Data Management to enable these exports.")

# ABOUT
elif page == "About":
    st.title("About TimanStat")
    st.caption(status_text(MODULES[page][0]))
    st.write("TimanStat is a Statistical Support Platform being developed under Timan Analytics.")
    st.write("Slogan: **Turning Data into Insights for Informed Decisions.**")
    st.write("This prototype currently supports CSV/Excel import, basic data-quality checks, descriptive statistics, basic charts and CSV exports.")
    st.warning("The presence of a module in navigation does not mean its analytical engine is implemented. Modules marked Under development are not operational.")

# ALL OTHER MODULES
