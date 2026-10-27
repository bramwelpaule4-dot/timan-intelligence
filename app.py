
    df = st.session_state.dataset
    if df is not None:
        st.subheader("Dataset preview")
        st.caption(f"File: {st.session_state.dataset_name or 'Uploaded dataset'}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Rows", f"{df.shape[0]:,}")
        m2.metric("Columns", f"{df.shape[1]:,}")
        m3.metric("Missing cells", f"{int(df.isna().sum().sum()):,}")
        st.dataframe(df.head(100), use_container_width=True)
        st.caption("Preview shows up to the first 100 rows. The full dataset remains loaded for analysis and export.")
        st.download_button(
            "Download imported dataset as CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="timan_dataset_export.csv",
            mime="text/csv",
        )

elif page == "Data Quality":
    st.title("Data Quality")
    st.caption("Module status: 🟢 Available — initial checks")
    df = get_dataset()
    if df is not None:
        m1, m2, m3 = st.columns(3)
        m1.metric("Rows", f"{len(df):,}")
        m2.metric("Columns", f"{len(df.columns):,}")
        m3.metric("Duplicate rows", f"{int(df.duplicated().sum()):,}")
        quality = pd.DataFrame({
            "variable": df.columns.astype(str),
            "data_type": [str(dtype) for dtype in df.dtypes],
            "missing_count": [int(df[col].isna().sum()) for col in df.columns],
            "missing_percent": [round(float(df[col].isna().mean() * 100), 2) for col in df.columns],
            "unique_values": [int(df[col].nunique(dropna=True)) for col in df.columns],
        })
        st.dataframe(quality, use_container_width=True)
        st.caption("These are diagnostic checks only. No rows or values have been changed or removed.")
        st.download_button("Download data-quality profile", quality.to_csv(index=False).encode("utf-8-sig"), "timan_data_quality.csv", "text/csv")

elif page == "Descriptive Statistics":
    st.title("Descriptive Statistics")
    st.caption("Module status: 🟢 Available — core functions")
    df = get_dataset()
    if df is not None:
        st.subheader("Numeric summary")
        summary = numeric_summary(df)
        if summary.empty or len(df.select_dtypes(include="number").columns) == 0:
            st.info("No numeric columns were detected. Check the imported column types.")
        else:
            st.dataframe(summary.round(4), use_container_width=True)
            st.download_button("Download numeric summary", summary.to_csv(index=False).encode("utf-8-sig"), "timan_numeric_summary.csv", "text/csv")
        st.subheader("Categorical frequency table")
        column = st.selectbox("Select a variable", options=list(df.columns), key="frequency_column")
        include_missing = st.checkbox("Include missing values as a category", value=True)
        counts = df[column].value_counts(dropna=not include_missing)
        denom = int(counts.sum())
        freq = counts.rename_axis("category").reset_index(name="count")
        freq["percent"] = (freq["count"] / denom * 100).round(2) if denom else 0.0
        st.dataframe(freq, use_container_width=True)
        st.caption("Percentages are unweighted. Complex survey designs and survey weights are not applied.")
        st.download_button("Download frequency table", freq.to_csv(index=False).encode("utf-8-sig"), "timan_frequency_table.csv", "text/csv")

elif page == "Visualisations":
    st.title("Visualisations")
    st.caption("Module status: 🟢 Available — core charts")
    df = get_dataset()
    if df is not None:
        chart_type = st.selectbox("Chart type", ["Bar chart", "Histogram", "Line chart", "Scatter plot"])
        numeric_cols = list(df.select_dtypes(include="number").columns)
        all_cols = list(df.columns)
        if chart_type == "Bar chart":
            column = st.selectbox("Category variable", all_cols, key="bar_col")
            top_n = st.slider("Maximum categories to display", 5, 50, 20, key="bar_top_n")
            values = df[column].astype("string").fillna("[Missing]").value_counts().head(top_n)
            st.bar_chart(values)
            st.caption("Bar chart displays the most frequent categories; values are counts.")
        elif chart_type == "Histogram":
            if not numeric_cols:
                st.warning("A histogram requires at least one numeric column.")
            else:
                column = st.selectbox("Numeric variable", numeric_cols, key="hist_col")
                bins = st.slider("Number of bins", 5, 50, 10)
                series = pd.to_numeric(df[column], errors="coerce").dropna()
                if series.empty:
                    st.warning("This variable has no valid numeric observations.")
                else:
                    categories = pd.cut(series, bins=min(bins, max(1, series.nunique())))
                    st.bar_chart(categories.value_counts(sort=False))
        elif chart_type == "Line chart":
            if not numeric_cols:
                st.warning("A line chart requires at least one numeric column.")
            else:
                column = st.selectbox("Numeric variable", numeric_cols, key="line_col")
                st.line_chart(df[[column]].reset_index(drop=True))
                st.caption("The horizontal axis is row order; it is not a date axis unless you prepare one separately.")
        else:
            if len(numeric_cols) < 2:
                st.warning("A scatter plot requires at least two numeric columns.")
            else:
                x_col = st.selectbox("X variable", numeric_cols, key="scatter_x")
                y_options = [col for col in numeric_cols if col != x_col]
                y_col = st.selectbox("Y variable", y_options, key="scatter_y")
                st.scatter_chart(df, x=x_col, y=y_col)

elif page == "Reports & Exports":
    st.title("Reports & Exports")
    st.caption("Module status: 🟢 Available — data exports; narrative reports under development")
    df = get_dataset()
    if df is not None:
        st.subheader("Dataset export")
        st.download_button("Download dataset as CSV", df.to_csv(index=False).encode("utf-8-sig"), "timan_dataset_export.csv", "text/csv")
        st.subheader("Descriptive statistics export")
        summary = numeric_summary(df)
        if summary.empty:
            st.info("No numeric columns are available for a numeric summary export.")
        else:
            st.dataframe(summary.round(4), use_container_width=True)
            st.download_button("Download numeric summary as CSV", summary.to_csv(index=False).encode("utf-8-sig"), "timan_numeric_summary.csv", "text/csv")
        st.info("Automatically written narrative reports and PDF report generation are Under development.")

elif page == "About":
    st.title("About Timan Intelligence")
    st.caption("Module status: 🟢 Available")
    st.write("Timan Intelligence is an AI-powered statistical analytics platform under Timan Analytics.")
    st.write("Slogan: **Turning Data into Insights for Informed Decisions.**")
    st.warning("This is an early prototype. Only the features explicitly marked available are presented as operational. Advanced analysis and the AI Analyst are Under development.")

else:
    show_under_development(page, MODULES[page][1])
