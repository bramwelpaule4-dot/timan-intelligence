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
