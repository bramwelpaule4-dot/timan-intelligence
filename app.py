
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
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title=f"{APP_NAME} | {APP_ORGANISATION}",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# APPLICATION CONSTANTS
# ============================================================

APP_ROOT = Path(__file__).resolve().parent

MODULES = {
    "Home": (
        "Available",
        "Welcome to TimanStat.",
    ),
    "Upload & Explore": (
        "Available",
        "Upload, inspect and explore datasets.",
    ),
    "Data Quality": (
        "Available",
        "Review dataset completeness, consistency and quality.",
    ),
    "Descriptive Statistics": (
        "Available",
        "Explore descriptive statistics and distributions.",
    ),
    "Statistical Analysis": (
        "Under development",
        "Conduct statistical analyses using validated methods.",
    ),
    "Visualisations": (
        "Available",
        "Explore data through visual summaries and charts.",
    ),
    "Ask Your Data": (
        "Under development",
        "Interact with your data using natural-language questions.",
    ),
    "Reports": (
        "Under development",
        "Prepare analytical reports and exports.",
    ),
    "Project Status": (
        "Available — implementation monitoring",
        "Monitor feature implementation, verification and project progress.",
    ),
    "About": (
        "Available",
        "Learn about TimanStat and its current capabilities.",
    ),
}


# ============================================================
# SESSION STATE
# ============================================================

if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = None

if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "Home"


# ============================================================
# SHARED HELPERS
# ============================================================

def show_header():
    """Display the main application identity."""

    st.markdown(
        f"""
        <div style="padding: 0.5rem 0 1rem 0;">
            <h1 style="margin-bottom: 0.1rem;">🔷 {APP_NAME}</h1>
            <p style="font-size: 1.05rem; margin-top: 0;">
                {APP_TAGLINE}
            </p>
            <p style="color: grey; margin-top: 0;">
                {PLATFORM_LABEL} | {APP_ORGANISATION}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_under_development(page, description):
    """Display a clear notice for modules not yet operational."""

    st.title(page)
    st.info("This module is currently under development.")
    st.write(description)
    st.warning(
        "The presence of a module in navigation does not mean its "
        "analytical engine is implemented. Modules marked "
        "Under development are not operational."
    )


def get_dataset():
    """Return the currently uploaded dataset, if available."""

    return st.session_state.uploaded_data


def set_dataset(data, filename):
    """Store the uploaded dataset in the application session."""

    st.session_state.uploaded_data = data
    st.session_state.uploaded_filename = filename


def require_dataset():
    """Check whether a dataset has been uploaded."""

    data = get_dataset()

    if data is None:
        st.warning("Please upload a dataset before using this module.")
        return None

    return data


def display_dataset_information(data):
    """Display basic dataset information."""

    col1, col2, col3 = st.columns(3)

    col1.metric("Rows", data.shape[0])
    col2.metric("Columns", data.shape[1])
    col3.metric("Missing cells", int(data.isna().sum().sum()))

    st.write("**Column names**")
    st.write(list(data.columns))


def dataframe_download(data, filename):
    """Provide a CSV download for a dataframe."""

    csv_data = data.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download CSV",
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:
    st.markdown(f"## 🔷 {APP_NAME}")
    st.caption(APP_ORGANISATION)

    st.divider()

    page = st.radio(
        "Navigation",
        list(MODULES.keys()),
        index=list(MODULES.keys()).index(
            st.session_state.selected_page
        ),
        key="navigation_page",
    )

    st.session_state.selected_page = page

    st.divider()

    st.caption(SIDEBAR_FOOTER)
    st.caption(f"Version {APP_VERSION}")


# ============================================================
# MAIN APPLICATION HEADER
# ============================================================

show_header()


# ============================================================
# HOME
# ============================================================

if page == "Home":

    st.title("Welcome to TimanStat")

    st.write(
        "TimanStat is a statistical analytics platform developed "
        "by Timan Analytics to support data exploration, quality "
        "assessment, statistical analysis and reporting."
    )

    st.info(
        "The current application is an active prototype. "
        "Some modules are operational while others remain under "
        "development."
    )

    st.subheader("Available capabilities")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            - Dataset upload
            - Dataset preview
            - Initial data-quality checks
            - Descriptive statistics
            """
        )

    with col2:
        st.markdown(
            """
            - Basic visualisations
            - Selected data exports
            - Project implementation monitoring
            """
        )

    st.subheader("Getting started")

    st.write(
        "Use the navigation menu to upload a dataset, explore "
        "its structure, review data quality and generate "
        "descriptive summaries."
    )


# ============================================================
# UPLOAD AND EXPLORE
# ============================================================

elif page == "Upload & Explore":

    st.title("Upload & Explore Data")

    st.write(
        "Upload a CSV or Excel dataset for initial inspection."
    )

    uploaded_file = st.file_uploader(
        "Choose a dataset",
        type=["csv", "xlsx", "xls"],
    )

    if uploaded_file is not None:

        try:
            file_extension = Path(uploaded_file.name).suffix.lower()

            if file_extension == ".csv":
                data = pd.read_csv(uploaded_file)

            elif file_extension in [".xlsx", ".xls"]:
                data = pd.read_excel(uploaded_file)

            else:
                st.error("Unsupported file format.")
                data = None

            if data is not None:

                set_dataset(data, uploaded_file.name)

                st.success(
                    f"Successfully uploaded {uploaded_file.name}"
                )

                st.subheader("Dataset preview")

                st.dataframe(
                    data.head(100),
                    use_container_width=True,
                )

                st.subheader("Dataset information")

                display_dataset_information(data)

        except Exception as error:
            st.error(
                f"Unable to read the uploaded dataset: {error}"
            )

    else:

        existing_data = get_dataset()

        if existing_data is not None:

            st.info(
                f"Current dataset: "
                f"{st.session_state.uploaded_filename}"
            )

            st.dataframe(
                existing_data.head(100),
                use_container_width=True,
            )

            display_dataset_information(existing_data)


# ============================================================
# DATA QUALITY
# ============================================================

elif page == "Data Quality":

    st.title("Data Quality Assessment")

    data = require_dataset()

    if data is not None:

        st.subheader("Dataset completeness")

        total_cells = data.shape[0] * data.shape[1]
        missing_cells = int(data.isna().sum().sum())

        completeness = (
            100 * (total_cells - missing_cells) / total_cells
            if total_cells > 0
            else 0
        )

        col1, col2, col3 = st.columns(3)

        col1.metric("Total cells", total_cells)
        col2.metric("Missing cells", missing_cells)
        col3.metric(
            "Completeness",
            f"{completeness:.2f}%",
        )

        st.subheader("Missing values by variable")

        missing_summary = pd.DataFrame(
            {
                "Variable": data.columns,
                "Missing values": data.isna().sum().values,
                "Missing percentage": (
                    data.isna().mean().values * 100
                ),
            }
        )

        st.dataframe(
            missing_summary,
            use_container_width=True,
        )

        st.subheader("Duplicate records")

        duplicate_count = int(data.duplicated().sum())

        st.metric(
            "Duplicate rows",
            duplicate_count,
        )

        st.subheader("Data types")

        dtype_summary = pd.DataFrame(
            {
                "Variable": data.columns,
                "Data type": [
                    str(dtype) for dtype in data.dtypes
                ],
            }
        )

        st.dataframe(
            dtype_summary,
            use_container_width=True,
        )

        st.subheader("Unique values")

        unique_summary = pd.DataFrame(
            {
                "Variable": data.columns,
                "Unique values": [
                    data[column].nunique(dropna=True)
                    for column in data.columns
                ],
            }
        )

        st.dataframe(
            unique_summary,
            use_container_width=True,
        )


# ============================================================
# DESCRIPTIVE STATISTICS
# ============================================================

elif page == "Descriptive Statistics":

    st.title("Descriptive Statistics")

    data = require_dataset()

    if data is not None:

        numeric_data = data.select_dtypes(
            include=np.number
        )

        categorical_data = data.select_dtypes(
            exclude=np.number
        )

        st.subheader("Numerical variables")

        if not numeric_data.empty:

            st.dataframe(
                numeric_data.describe().T,
                use_container_width=True,
            )

        else:
            st.info(
                "No numerical variables were detected."
            )

        st.subheader("Categorical variables")

        if not categorical_data.empty:

            selected_column = st.selectbox(
                "Select a categorical variable",
                categorical_data.columns,
            )

            frequency_table = (
                data[selected_column]
                .value_counts(dropna=False)
                .rename_axis("Category")
                .reset_index(name="Frequency")
            )

            frequency_table["Percentage"] = (
                frequency_table["Frequency"]
                / len(data)
                * 100
            )

            st.dataframe(
                frequency_table,
                use_container_width=True,
            )

        else:
            st.info(
                "No categorical variables were detected."
            )


# ============================================================
# STATISTICAL ANALYSIS
# ============================================================

elif page == "Statistical Analysis":

    show_under_development(
        page,
        MODULES[page][1],
    )


# ============================================================
# VISUALISATIONS
# ============================================================

elif page == "Visualisations":

    st.title("Data Visualisations")

    data = require_dataset()

    if data is not None:

        numeric_columns = data.select_dtypes(
            include=np.number
        ).columns.tolist()

        if len(numeric_columns) >= 1:

            st.subheader("Numerical variable distribution")

            selected_variable = st.selectbox(
                "Select a numerical variable",
                numeric_columns,
            )

            st.bar_chart(
                data[selected_variable].value_counts().sort_index()
            )

            st.subheader("Numerical summary")

            st.write(
                data[selected_variable].describe()
            )

        else:
            st.info(
                "No numerical variables are available for plotting."
            )


# ============================================================
# ASK YOUR DATA
# ============================================================

elif page == "Ask Your Data":

    show_under_development(
        page,
        MODULES[page][1],
    )


# ============================================================
# REPORTS
# ============================================================

elif page == "Reports":

    show_under_development(
        page,
        MODULES[page][1],
    )


# ============================================================
# PROJECT STATUS DASHBOARD
# ============================================================

elif page == "Project Status":

    render_project_status_dashboard()


# ============================================================
# ABOUT
# ============================================================

elif page == "About":

    st.title(f"About {APP_NAME}")

    st.subheader(APP_TAGLINE)

    st.write(APP_DESCRIPTION)

    st.markdown(
        f"""
        **Organisation:** {APP_ORGANISATION}

        **Version:** {APP_VERSION}

        **Description:** {SHORT_DESCRIPTION}
        """
    )

    st.subheader("Development status")

    st.write(
        "TimanStat is being developed as a statistical support "
        "platform for data exploration, statistical analysis, "
        "visualisation and reporting."
    )

    st.warning(
        "The application is under active development. "
        "Additional modules remain under development."
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
