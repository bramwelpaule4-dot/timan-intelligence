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
        st.download_button(
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
        st.download_button(
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
                st.download_button(
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
            st.download_button(
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
            st.download_button(
                "Download full numeric summary",
                data=summary.to_csv(index=False).encode("utf-8-sig"),
                file_name="timan_descriptive_statistics.csv",
                mime="text/csv",
                key="download_numeric_summary",
            )

            st.caption(
                "Interpretation guide: the mean is sensitive to extreme values; "
                "the median is more resistant. Standard deviation describes "
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
            st.download_button(
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
            st.download_button(
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
            st.download_button(
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
