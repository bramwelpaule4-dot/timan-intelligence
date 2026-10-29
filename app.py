
import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIGURATION AND BRANDING
# ============================================================

st.set_page_config(
    page_title="TimanStat",
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
    "Settings & Governance": (
        "Under development",
        "Authentication, tenant isolation and audit controls are not implemented.",
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
    """Create a variable-level data-quality summary."""
    missing = df.isna().sum()
    row_count = len(df)

    return pd.DataFrame(
        {
            "Variable": df.columns.astype(str),
            "Data type": [str(dtype) for dtype in df.dtypes],
            "Missing values": [
                int(missing[col]) for col in df.columns
            ],
            "Missing (%)": [
                round(float(missing[col]) / row_count * 100, 2)
                if row_count
                else 0.0
                for col in df.columns
            ],
            "Unique values": [
                int(df[col].nunique(dropna=True))
                for col in df.columns
            ],
        }
    )


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

logo_path = Path(__file__).parent / "timan_analytics_logo.png"

if logo_path.exists():
    st.sidebar.image(
        str(logo_path),
        use_container_width=True,
    )
else:
    st.sidebar.markdown(
        """
        <div style="
            text-align:center;
            padding:16px 6px;
            border:1px dashed #8aa1b8;
            border-radius:12px;
        ">
            <strong>Timan Analytics logo</strong><br/>
            <small>Add timan_analytics_logo.png beside app.py</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    """
    <div style="text-align:center; padding:4px 4px 8px;">
        <div style="
            font-size:25px;
            font-weight:800;
            color:#174a7e;
            margin-top:4px;
        ">
            TimanStat
        </div>
        <div style="
            font-size:11px;
            font-weight:700;
            letter-spacing:.6px;
            color:#526579;
            margin-top:3px;
        ">
            STATISTICAL SUPPORT PLATFORM
        </div>
        <div style="
            font-size:12px;
            color:#526579;
            margin-top:7px;
        ">
            by Timan Analytics
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    list(MODULES.keys()),
    key="navigation_page",
)

st.sidebar.divider()
st.sidebar.caption(
    "Statistical Expertise. Data-Driven Decisions."
)

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
        '<div class="brand">TIMANSTAT</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="subtitle">'
        "Turning Data into Insights for Informed Decisions."
        "</div>",
        unsafe_allow_html=True,
    )

    st.write("")

    st.write(
        "TimanStat is a statistical analytics platform for "
        "exploring datasets, checking data quality, calculating "
        "descriptive statistics and creating basic visualisations."
    )

    df = st.session_state.dataset

    if df is None:
        a, b, c = st.columns(3)

        a.metric("Dataset status", "Not loaded")
        b.metric("Available formats", "CSV / Excel")
        c.metric("Navigation modules", len(MODULES))

        st.info(
            "To begin, select Data Management from the left "
            "navigation and upload a CSV or Excel file."
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
        c.metric(
            "Missing cells",
            f"{int(df.isna().sum().sum()):,}",
        )

        st.subheader("Dataset preview")
        st.dataframe(
            df.head(10),
            use_container_width=True,
        )

        st.caption(
            f"Current dataset: {st.session_state.dataset_name}"
        )

    st.subheader("Module availability")

    status_rows = [
        {
            "Module": name,
            "Status": status,
            "Purpose": purpose,
        }
        for name, (status, purpose) in MODULES.items()
    ]

    st.dataframe(
        pd.DataFrame(status_rows),
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

        # CSV: import directly when a different file is uploaded.
        if file_name.endswith(".csv"):
            if (
                st.session_state.dataset_source_key != upload_key
                or st.session_state.dataset is None
            ):
                try:
                    imported = load_uploaded_file(uploaded_file)

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

        st.download_button(
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

    df = get_dataset()

    if df is not None:
        quality = variable_quality_profile(df)

        a, b, c = st.columns(3)

        a.metric("Rows", f"{len(df):,}")
        b.metric(
            "Duplicate rows",
            f"{int(df.duplicated().sum()):,}",
        )
        c.metric(
            "Missing cells",
            f"{int(df.isna().sum().sum()):,}",
        )

        st.subheader("Variable-level quality profile")

        st.dataframe(
            quality,
            hide_index=True,
            use_container_width=True,
        )

        st.caption(
            "No rows are removed, and no values are imputed or "
            "recoded by this report. Duplicate rows are flagged, "
            "not automatically deleted."
        )

        st.download_button(
            "Download data-quality profile",
            data=quality.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_data_quality.csv",
            mime="text/csv",
            key="download_quality",
        )


# ============================================================
# DESCRIPTIVE STATISTICS
# ============================================================

elif page == "Descriptive Statistics":
    st.title("Descriptive Statistics")
    st.caption(status_text(MODULES[page][0]))

    df = get_dataset()

    if df is not None:
        st.subheader("Numeric summary")

        summary = numeric_summary(df)

        if summary.empty:
            st.info(
                "No numeric columns were detected. Check whether "
                "numeric values were imported as text."
            )

        else:
            st.dataframe(
                summary,
                hide_index=True,
                use_container_width=True,
            )

            st.download_button(
                "Download numeric summary",
                data=summary.to_csv(index=False).encode("utf-8-sig"),
                file_name="timan_descriptive_statistics.csv",
                mime="text/csv",
                key="download_numeric_summary",
            )

        categorical_columns = [
            col
            for col in df.columns
            if not pd.api.types.is_numeric_dtype(df[col].dtype)
        ]

        if categorical_columns:
            st.subheader("Categorical frequency table")

            selected_col = st.selectbox(
                "Select a categorical variable",
                categorical_columns,
                format_func=str,
            )

            include_missing = st.checkbox(
                "Show missing values as a category",
                value=True,
            )

            series = df[selected_col].astype("object")

            if include_missing:
                series = series.where(
                    series.notna(),
                    "(Missing)",
                )
                counts = series.value_counts(dropna=False)
                denominator = len(df)

            else:
                series = series.dropna()
                counts = series.value_counts(dropna=True)
                denominator = len(series)

            frequencies = (
                counts.rename_axis("Category")
                .reset_index(name="Frequency")
            )

            frequencies["Percentage (%)"] = (
                (frequencies["Frequency"] / denominator * 100).round(2)
                if denominator
                else 0.0
            )

            st.dataframe(
                frequencies,
                hide_index=True,
                use_container_width=True,
            )

            st.caption(
                f"Percentage denominator: {denominator:,} records"
                + (
                    " (including missing values)."
                    if include_missing
                    else " (non-missing records only)."
                )
            )

            st.download_button(
                "Download frequency table",
                data=frequencies.to_csv(index=False).encode("utf-8-sig"),
                file_name="timan_frequency_table.csv",
                mime="text/csv",
                key="download_frequency_table",
            )

        else:
            st.info(
                "No non-numeric columns were detected for "
                "categorical frequency tables."
            )


# ============================================================
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

        quality = variable_quality_profile(df)

        st.download_button(
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
# ABOUT
# ============================================================

elif page == "About":
    st.title("About TimanStat")
    st.caption(status_text(MODULES[page][0]))

    st.write(
        "TimanStat is a Statistical Support Platform being "
        "developed under Timan Analytics."
    )

    st.write(
        "Slogan: **Turning Data into Insights for Informed Decisions.**"
    )

    st.write(
        "The current prototype supports CSV and Excel import, "
        "worksheet selection, basic data-quality checks, descriptive "
        "statistics, basic charts and CSV exports."
    )

    st.warning(
        "The presence of a module in navigation does not mean its "
        "analytical engine is implemented. Modules marked "
        "Under development are not operational."
    )


# ============================================================
# ALL OTHER MODULES
# ============================================================

else:
    show_under_development(
        page,
        MODULES[page][1],
    )
