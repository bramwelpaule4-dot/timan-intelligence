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
