# TIMANSTAT STATISTICAL METHODS CATALOGUE

**Version:** 1.0 — Proposed architecture  
**Purpose:** Establish the statistical scope, classification hierarchy and method identifiers for TimanStat.

## 1. DESCRIPTIVE STATISTICS

Descriptive statistics summarise, organise and present the characteristics of observed data.

### 1.1 Frequency and distribution
- Frequency distribution — `frequency_distribution`
- Relative frequency — `relative_frequency`
- Cumulative frequency — `cumulative_frequency`
- Proportions and percentages — `proportions_percentages`
- Grouped frequency distribution — `grouped_frequency_distribution`
- Cross-tabulation — `cross_tabulation`

### 1.2 Measures of central tendency
- Arithmetic mean — `arithmetic_mean`
- Weighted mean — `weighted_mean`
- Geometric mean — `geometric_mean`
- Harmonic mean — `harmonic_mean`
- Median — `median`
- Mode — `mode`
- Trimmed mean — `trimmed_mean`

### 1.3 Measures of dispersion
- Minimum and maximum — `minimum_maximum`
- Range — `range`
- Interquartile range — `interquartile_range`
- Quartile deviation — `quartile_deviation`
- Mean absolute deviation — `mean_absolute_deviation`
- Variance — `variance`
- Standard deviation — `standard_deviation`
- Coefficient of variation — `coefficient_of_variation`
- Median absolute deviation — `median_absolute_deviation`

### 1.4 Measures of position
- Quartiles — `quartiles`
- Deciles — `deciles`
- Percentiles — `percentiles`
- Quantiles — `quantiles`
- Z-scores — `z_scores`
- Rank statistics — `rank_statistics`

### 1.5 Measures of distribution shape
- Skewness — `skewness`
- Kurtosis — `kurtosis`
- Excess kurtosis — `excess_kurtosis`

### 1.6 Descriptive relationship measures
- Covariance — `covariance`
- Pearson correlation coefficient — `pearson_correlation`
- Spearman rank correlation coefficient — `spearman_correlation`
- Kendall's tau — `kendall_tau`
- Phi coefficient — `phi_coefficient`
- Cramér's V — `cramers_v`

### 1.7 Graphical and visual analysis
- Bar chart — `bar_chart`
- Pie chart — `pie_chart`
- Histogram — `histogram`
- Frequency polygon — `frequency_polygon`
- Ogive — `ogive`
- Box plot — `box_plot`
- Violin plot — `violin_plot`
- Scatter plot — `scatter_plot`
- Line graph — `line_graph`
- Density plot — `density_plot`
- Heatmap — `heatmap`
- Stem-and-leaf plot — `stem_leaf_plot`
- Dot plot — `dot_plot`
- Q–Q plot — `qq_plot`

### 1.8 Exploratory data and outlier analysis
- Outlier identification — `outlier_detection`
- Empirical distribution analysis — `empirical_distribution`
- Missing-data profile — `missing_data_profile`
- Duplicate-record analysis — `duplicate_analysis`

## 2. INFERENTIAL STATISTICS

Inferential statistics uses sample data, probability models and statistical assumptions to estimate population parameters, test hypotheses and investigate relationships.

### 2.1 Estimation
- Point estimation — `point_estimation`
- Interval estimation — `interval_estimation`
- Confidence intervals — `confidence_interval`
- Standard errors — `standard_error`
- Margin of error — `margin_of_error`
- Bootstrap estimation — `bootstrap_estimation`

### 2.2 Hypothesis testing
- One-sample hypothesis test — `one_sample_test`
- One-tailed test — `one_tailed_test`
- Two-tailed test — `two_tailed_test`
- Statistical power analysis — `power_analysis`
- Multiple-testing correction — `multiple_testing_correction`

### 2.3 Tests of differences

**Parametric methods**
- One-sample t-test — `one_sample_t_test`
- Independent-samples Student's t-test — `student_independent_t_test`
- Welch's independent-samples t-test — `welch_independent_t_test`
- Paired-samples t-test — `paired_t_test`
- One-way ANOVA — `one_way_anova`
- Two-way ANOVA — `two_way_anova`
- Factorial ANOVA — `factorial_anova`
- Repeated-measures ANOVA — `repeated_measures_anova`
- ANCOVA — `ancova`
- MANOVA — `manova`

**Non-parametric methods**
- Mann–Whitney U test — `mann_whitney_u`
- Wilcoxon signed-rank test — `wilcoxon_signed_rank`
- Kruskal–Wallis test — `kruskal_wallis`
- Friedman test — `friedman_test`
- Mood's median test — `mood_median_test`

### 2.4 Tests of categorical data
- Chi-square goodness-of-fit test — `chi_square_goodness_of_fit`
- Chi-square test of independence — `chi_square_independence`
- Chi-square test of homogeneity — `chi_square_homogeneity`
- Fisher's exact test — `fisher_exact`
- McNemar's test — `mcnemar_test`
- Cochran's Q test — `cochrans_q`
- Two-proportion z-test — `two_proportion_z_test`
- Binomial test — `binomial_test`

### 2.5 Correlation and association inference
- Pearson correlation test — `pearson_correlation_test`
- Spearman correlation test — `spearman_correlation_test`
- Kendall's tau test — `kendall_tau_test`
- Partial correlation test — `partial_correlation_test`
- Point-biserial correlation test — `point_biserial_test`

### 2.6 Regression and predictive modelling
**Linear regression**
- Simple linear regression — `simple_linear_regression`
- Multiple linear regression — `multiple_linear_regression`
- Polynomial regression — `polynomial_regression`
- Interaction regression — `interaction_regression`
- Weighted least squares — `weighted_least_squares`

**Generalised linear models**
- Binary logistic regression — `binary_logistic_regression`
- Multinomial logistic regression — `multinomial_logistic_regression`
- Ordinal logistic regression — `ordinal_logistic_regression`
- Poisson regression — `poisson_regression`
- Negative binomial regression — `negative_binomial_regression`

**Other regression methods**
- Robust regression — `robust_regression`
- Quantile regression — `quantile_regression`
- Ridge regression — `ridge_regression`
- Lasso regression — `lasso_regression`
- Elastic net regression — `elastic_net_regression`

### 2.7 Model testing and comparison
- F-test — `f_test`
- Likelihood-ratio test — `likelihood_ratio_test`
- Wald test — `wald_test`
- Score test — `score_test`
- Goodness-of-fit test — `goodness_of_fit_test`
- Nested-model comparison — `nested_model_comparison`
- Residual analysis — `residual_analysis`

### 2.8 Survival analysis
- Kaplan–Meier estimator — `kaplan_meier`
- Log-rank test — `log_rank_test`
- Cox proportional hazards regression — `cox_proportional_hazards`
- Survival probability estimation — `survival_probability`
- Hazard ratio estimation — `hazard_ratio`

### 2.9 Time-series analysis
- Autocorrelation — `autocorrelation`
- Partial autocorrelation — `partial_autocorrelation`
- Stationarity testing — `stationarity_test`
- Trend analysis — `trend_analysis`
- Seasonal analysis — `seasonal_analysis`
- ARIMA — `arima`
- Exponential smoothing — `exponential_smoothing`
- Time-series forecasting — `time_series_forecasting`

### 2.10 Resampling and simulation-based inference
- Bootstrap inference — `bootstrap_inference`
- Permutation test — `permutation_test`
- Randomisation test — `randomisation_test`
- Monte Carlo simulation — `monte_carlo_simulation`

## 3. CROSS-CUTTING STATISTICAL CAPABILITIES

These are shared capabilities, not independent statistical branches or necessarily standalone methods.

### 3.1 Assumption assessment
- Normality assessment
- Homogeneity of variance
- Independence assessment
- Linearity assessment
- Multicollinearity assessment
- Residual diagnostics
- Distributional and model-specific diagnostics

### 3.2 Effect sizes
- Cohen's d
- Hedges' g
- Eta-squared
- Partial eta-squared
- Omega-squared
- Cramér's V
- Phi coefficient
- Correlation coefficient
- Odds ratio
- Risk ratio
- Risk difference
- Regression coefficients
- R-squared and adjusted R-squared
- Hazard ratio

### 3.3 Confidence intervals
- Confidence intervals for means
- Confidence intervals for proportions
- Confidence intervals for differences
- Confidence intervals for correlations
- Confidence intervals for effect sizes
- Confidence intervals for regression parameters
- Confidence intervals for ratios and hazard measures

### 3.4 Common reporting
- Research question
- Hypotheses, where applicable
- Method selection rationale
- Test statistic, where applicable
- Degrees of freedom, where applicable
- P-value, where applicable
- Effect size, where appropriate
- Confidence interval, where appropriate
- Assumptions and diagnostics
- Limitations
- Contextual interpretation

## 4. ARCHITECTURAL CLASSIFICATION

Every catalogue entry should have:

1. A unique method identifier.
2. A statistical branch.
3. A statistical family.
4. A human-readable method name.
5. Required variable types and roles.
6. Applicable assumptions.
7. Applicable outputs and reporting measures.
8. An implementation status.

## 5. IMPLEMENTATION STATUS

Methods must be classified separately from their statistical recognition.

- `planned` — included in the catalogue but not implemented.
- `in_development` — implementation is underway.
- `implemented` — calculation is available.
- `tested` — automated tests pass.
- `validated` — numerical behaviour has been checked against trusted statistical references.

A method must not be presented as operational merely because it appears in the catalogue.

## 6. FUTURE EXTENSIONS

The architecture should allow additional statistical domains, including:

- Bayesian statistics
- Multivariate statistics
- Multilevel and hierarchical modelling
- Survey sampling and complex survey analysis
- Causal inference
- Spatial statistics
- Epidemiological methods
- Design of experiments

These extensions should be added through the same branch–family–method hierarchy.
