line height from the view settings menu.

‎app.py‎
+266
Lines changed: 266 additions & 0 deletions
Original file line number	Diff line number	Diff line change
@@ -0,0 +1,266 @@
import streamlit as st
import pandas as pd
import io
st.set_page_config(
    page_title="Timan Intelligence",
    page_icon="📊",
    layout="wide"
)
# Brand styling
st.markdown("""
<style>
    .main {
        background-color: #f7f9fc;
    }
    .brand {
        color: #174a7e;
        font-size: 34px;
        font-weight: 800;
    }
    .subtitle {
        color: #526579;
        font-size: 16px;
    }
    div[data-testid="stMetric"] {
        background: white;
        padding: 16px;
        border-radius: 10px;
        border: 1px solid #e3eaf2;
    }
</style>
""", unsafe_allow_html=True)
st.sidebar.markdown("## 🔷 TIMAN")
st.sidebar.caption("INTELLIGENCE")
page = st.sidebar.radio(
    "NAVIGATION",
    ["Home", "Upload & Explore", "Statistical Analysis",
     "Visualisations", "Ask Your Data", "Reports", "About"]
)
st.sidebar.divider()
st.sidebar.caption("Turning Data into Insights for Informed Decisions.")
if "dataset" not in st.session_state:
    st.session_state.dataset = None
df = st.session_state.dataset
if page == "Home":
    st.markdown('<div class="brand">TIMAN INTELLIGENCE</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">AI-powered statistical analytics by Timan Analytics</div>',
        unsafe_allow_html=True
    )
    st.divider()
    st.title("Welcome to your data intelligence workspace")
    st.write(
        "Transform raw data into meaningful statistics, visualisations "
        "and evidence for better decisions."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Platform", "Analytics")
    c2.metric("Data formats", "CSV / Excel")
    c3.metric("AI assistant", "Coming soon")
    st.subheader("Get started")
    st.write("Use the navigation menu to upload a dataset and explore its contents.")
    st.info(
        "This is the initial prototype. Statistical results are calculated "
        "from your uploaded data. AI-powered question answering will be "
        "integrated in a later version."
    )
elif page == "Upload & Explore":
    st.title("Upload and explore your data")
    uploaded = st.file_uploader(
        "Choose a CSV or Excel file",
        type=["csv", "xlsx"]
    )
    if uploaded is not None:
        try:
            if uploaded.name.lower().endswith(".csv"):
                new_df = pd.read_csv(uploaded)
            else:
                new_df = pd.read_excel(uploaded)
            st.session_state.dataset = new_df
            df = new_df
            st.success("Dataset loaded successfully.")
        except Exception as e:
            st.error(f"Could not read this file: {e}")
    if df is not None:
        a, b, c = st.columns(3)
        a.metric("Rows", f"{df.shape[0]:,}")
        b.metric("Columns", f"{df.shape[1]:,}")
        c.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
        st.subheader("Data preview")
        st.dataframe(df.head(100), use_container_width=True)
        st.subheader("Variable information")
        info = pd.DataFrame({
            "Variable": df.columns.astype(str),
            "Data type": [str(x) for x in df.dtypes],
            "Missing values": df.isna().sum().values,
            "Unique values": df.nunique(dropna=True).values
        })
        st.dataframe(info, use_container_width=True)
        st.subheader("Data quality checks")
        duplicates = int(df.duplicated().sum())
        st.write(f"Completely duplicated rows: **{duplicates:,}**")
        st.write(
            f"Missing-value cells: **{int(df.isna().sum().sum()):,}**"
        )
    else:
        st.info("Upload a CSV or Excel file to begin.")
elif page == "Statistical Analysis":
    st.title("Statistical analysis")
    if df is None:
        st.info("Upload a dataset first using Upload & Explore.")
    else:
        numeric = df.select_dtypes(include="number")
        st.subheader("Descriptive statistics")
        if not numeric.empty:
            st.dataframe(numeric.describe().T, use_container_width=True)
        else:
            st.warning("No numeric variables were detected.")
        st.subheader("Frequency distribution")
        column = st.selectbox("Select a variable", df.columns)
        frequencies = (
            df[column].astype("string")
            .fillna("(Missing)")
            .value_counts()
            .rename_axis("Category")
            .reset_index(name="Frequency")
        )
        frequencies["Percentage"] = (
            frequencies["Frequency"] / len(df) * 100
            if len(df) > 0 else 0
        )
        st.dataframe(frequencies, use_container_width=True)
        st.subheader("Cross-tabulation")
        if len(df.columns) >= 2:
            col1, col2 = st.columns(2)
            with col1:
                row_var = st.selectbox(
                    "Rows", df.columns, key="cross_rows"
                )
            with col2:
                col_var = st.selectbox(
                    "Columns", df.columns, index=1, key="cross_cols"
                )
            if row_var != col_var:
                tab = pd.crosstab(
                    df[row_var], df[col_var], margins=True
                )
                st.dataframe(tab, use_container_width=True)
            else:
                st.warning("Choose two different variables.")
elif page == "Visualisations":
    st.title("Data visualisation")
    if df is None:
        st.info("Upload a dataset first.")
    else:
        chart_type = st.selectbox(
            "Chart type",
            ["Bar chart", "Histogram", "Line chart", "Scatter plot"]
        )
        numeric_cols = list(df.select_dtypes(include="number").columns)
        if chart_type == "Bar chart":
            variable = st.selectbox("Variable", df.columns)
            counts = df[variable].astype("string").fillna("(Missing)").value_counts()
            st.bar_chart(counts)
        elif chart_type == "Histogram":
            if numeric_cols:
                variable = st.selectbox("Numeric variable", numeric_cols)
                values = pd.to_numeric(df[variable], errors="coerce").dropna()
                hist = pd.cut(values, bins=min(10, max(1, values.nunique()))).value_counts().sort_index()
                st.bar_chart(hist)
            else:
                st.warning("No numeric variables available.")
        elif chart_type == "Line chart":
            if numeric_cols:
                variable = st.selectbox("Numeric variable", numeric_cols)
                st.line_chart(df[variable].dropna())
            else:
                st.warning("No numeric variables available.")
        elif chart_type == "Scatter plot":
            if len(numeric_cols) >= 2:
                x = st.selectbox("X-axis", numeric_cols)
                y = st.selectbox(
                    "Y-axis", numeric_cols,
                    index=1 if len(numeric_cols) > 1 else 0
                )
                st.scatter_chart(df[[x, y]].dropna(), x=x, y=y)
            else:
                st.warning("At least two numeric variables are needed.")
elif page == "Ask Your Data":
    st.title("Ask your data")
    st.write(
        "In the future, you will be able to ask questions in plain English "
        "and receive answers based on verified statistical calculations."
    )
    st.text_area(
        "What would you like to know about your data?",
        placeholder="Example: Which category has the highest frequency?"
    )
    st.info(
        "AI question answering is not connected yet. This version does not "
        "generate answers to analytical questions."
    )
elif page == "Reports":
    st.title("Export your data and results")
    if df is None:
        st.info("Upload a dataset first.")
    else:
        st.download_button(
            "Download dataset as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="timan_data_export.csv",
            mime="text/csv"
        )
        st.download_button(
            "Download descriptive statistics as CSV",
            data=df.describe(include="all").T.to_csv().encode("utf-8"),
            file_name="timan_descriptive_statistics.csv",
            mime="text/csv"
        )
        st.caption(
            "These are data exports, not yet a complete narrative analytical report."
        )
elif page == "About":
    st.title("About Timan Intelligence")
    st.write(
        "Timan Intelligence is a developing analytics platform by Timan Analytics."
    )
    st.markdown("### Our focus")
    st.write("- Statistical data analysis")
    st.write("- Data visualisation and reporting")
    st.write("- Applied research")
    st.write("- Monitoring, Evaluation, Accountability and Learning")
    st.write("- AI-assisted interpretation of verified results")
    st.divider()
    st.caption("Turning Data into Insights for Informed Decisions.")
