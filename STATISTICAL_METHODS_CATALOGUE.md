# TIMANSTAT STATISTICAL METHODS CATALOGUE

**Version:** 2.0  
**Status:** Proposed comprehensive statistical blueprint  
**Product:** TimanStat  
**Organisation:** Timan Analytics

## 1. PURPOSE AND SCOPE

This catalogue establishes the statistical knowledge and methodological scope of TimanStat.

TimanStat is intended to support statistical analysis across general research, biostatistics, epidemiology, public health, economics, agriculture, education, business, social sciences and other quantitative disciplines.

The catalogue is designed to accommodate:

- Descriptive statistics.
- Probability theory and distributions.
- Classical and frequentist inference.
- Bayesian statistics.
- Experimental design.
- Sampling and survey statistics.
- Regression and generalised linear models.
- Multivariate statistics.
- Non-parametric statistics.
- Time-series analysis.
- Survival and event-history analysis.
- Spatial statistics.
- Causal inference.
- Statistical learning and predictive modelling.
- Stochastic processes.
- Reliability and quality statistics.
- Epidemiological statistics.
- Psychometrics and measurement theory.
- Statistical computing and simulation.

The catalogue defines what TimanStat should recognise and eventually support. Inclusion does not imply that a method is already implemented or validated.

---

# PART I: FOUNDATIONAL STATISTICS

## 2. DESCRIPTIVE STATISTICS

Descriptive statistics organise, summarise and present observed data.

### 2.1 Frequency and distribution analysis
- Frequency distribution
- Absolute frequency
- Relative frequency
- Cumulative frequency
- Cumulative relative frequency
- Proportions
- Percentages
- Grouped frequency distribution
- Frequency density
- Cross-tabulation
- Contingency tables
- Joint frequency distributions
- Marginal frequency distributions

### 2.2 Measures of central tendency
- Arithmetic mean
- Weighted arithmetic mean
- Geometric mean
- Harmonic mean
- Median
- Mode
- Trimmed mean
- Winsorised mean
- Midrange
- Trimean

### 2.3 Measures of dispersion
- Minimum and maximum
- Range
- Interquartile range
- Quartile deviation
- Mean absolute deviation
- Median absolute deviation
- Population variance
- Sample variance
- Population standard deviation
- Sample standard deviation
- Coefficient of variation
- Relative dispersion measures
- Average absolute deviation

### 2.4 Measures of position
- Quartiles
- Deciles
- Percentiles
- Quantiles
- Quintiles
- Z-scores
- Standard scores
- Percentile ranks
- Rank statistics

### 2.5 Measures of distribution shape
- Skewness
- Positive skewness
- Negative skewness
- Symmetry assessment
- Kurtosis
- Excess kurtosis
- Mesokurtic distribution
- Leptokurtic distribution
- Platykurtic distribution
- Higher-order moments

### 2.6 Descriptive association and relationship measures
- Covariance
- Pearson correlation coefficient
- Spearman rank correlation coefficient
- Kendall's tau
- Phi coefficient
- Cramér's V
- Contingency coefficient
- Point-biserial correlation coefficient
- Rank-biserial correlation coefficient

### 2.7 Graphical descriptive methods
- Bar chart
- Grouped bar chart
- Stacked bar chart
- Pie chart
- Histogram
- Frequency polygon
- Ogive
- Box plot
- Violin plot
- Dot plot
- Stem-and-leaf plot
- Scatter plot
- Bubble plot
- Line graph
- Density plot
- Empirical cumulative distribution plot
- Q–Q plot
- P–P plot
- Heatmap
- Mosaic plot
- Error-bar plot
- Population pyramid
- Pareto chart
- Radar chart

### 2.8 Exploratory data analysis
- Univariate analysis
- Bivariate analysis
- Multivariate exploratory analysis
- Distribution exploration
- Outlier identification
- Missing-data exploration
- Duplicate-record analysis
- Grouped descriptive analysis
- Stratified descriptive analysis
- Robust exploratory summaries

---

## 3. PROBABILITY THEORY AND DISTRIBUTIONS

Probability theory provides the mathematical foundation for statistical inference.

### 3.1 Probability fundamentals
- Classical probability
- Empirical probability
- Axiomatic probability
- Conditional probability
- Joint probability
- Marginal probability
- Independence of events
- Mutually exclusive events
- Bayes' theorem
- Law of total probability
- Combinatorics
- Permutations and combinations

### 3.2 Random variables
- Discrete random variables
- Continuous random variables
- Mixed random variables
- Probability mass functions
- Probability density functions
- Cumulative distribution functions
- Joint distributions
- Marginal distributions
- Conditional distributions

### 3.3 Probability moments and properties
- Mathematical expectation
- Variance
- Standard deviation
- Covariance
- Correlation
- Conditional expectation
- Moment-generating functions
- Characteristic functions
- Probability-generating functions
- Higher-order moments

### 3.4 Discrete probability distributions
- Bernoulli distribution
- Binomial distribution
- Geometric distribution
- Negative binomial distribution
- Hypergeometric distribution
- Poisson distribution
- Discrete uniform distribution
- Multinomial distribution
- Beta-binomial distribution

### 3.5 Continuous probability distributions
- Uniform distribution
- Normal distribution
- Standard normal distribution
- Exponential distribution
- Gamma distribution
- Beta distribution
- Chi-square distribution
- Student's t-distribution
- F-distribution
- Weibull distribution
- Log-normal distribution
- Logistic distribution
- Cauchy distribution
- Pareto distribution
- Laplace distribution
- Rayleigh distribution
- Gumbel distribution
- Inverse Gaussian distribution

### 3.6 Sampling distributions and limit theorems
- Sampling distributions
- Central Limit Theorem
- Law of Large Numbers
- Distribution of sample means
- Distribution of sample proportions
- Distribution of sample variance
- Standard error distributions
- Order-statistic distributions

---

# PART II: DESCRIPTIVE AND CLASSICAL INFERENTIAL ANALYSIS

## 4. CLASSICAL AND FREQUENTIST INFERENCE

### 4.1 Statistical estimation
- Point estimation
- Interval estimation
- Method of moments estimation
- Maximum likelihood estimation
- Least squares estimation
- Minimum variance estimation
- Unbiased estimation
- Consistent estimation
- Efficient estimation
- Sufficient statistics
- Fisher information
- Standard errors
- Margin of error

### 4.2 Confidence intervals
- Confidence interval for a population mean
- Confidence interval for a population proportion
- Confidence interval for a variance
- Confidence interval for a difference between means
- Confidence interval for a difference between proportions
- Confidence interval for correlation
- Confidence interval for regression coefficients
- Confidence interval for odds ratios
- Confidence interval for risk ratios
- Confidence interval for effect sizes
- Bootstrap confidence intervals
- Profile likelihood confidence intervals

### 4.3 Hypothesis testing
- Null and alternative hypotheses
- Simple and composite hypotheses
- One-tailed testing
- Two-tailed testing
- Significance levels
- P-values
- Critical-value methods
- Type I error
- Type II error
- Statistical power
- Minimum detectable effect
- Multiple-testing correction
- Family-wise error rate
- False discovery rate
- Bonferroni correction
- Holm correction
- Benjamini–Hochberg procedure

### 4.4 Tests of means and differences

**Parametric tests**
- One-sample t-test
- Independent-samples Student's t-test
- Welch's independent-samples t-test
- Paired-samples t-test
- One-way ANOVA
- Two-way ANOVA
- Factorial ANOVA
- N-way ANOVA
- Repeated-measures ANOVA
- Mixed-design ANOVA
- Analysis of covariance (ANCOVA)
- Multivariate analysis of variance (MANOVA)
- Multivariate analysis of covariance (MANCOVA)

**Non-parametric alternatives**
- One-sample sign test
- Two-sample sign test
- Mann–Whitney U test
- Wilcoxon signed-rank test
- Kruskal–Wallis test
- Friedman test
- Mood's median test
- Jonckheere–Terpstra test
- Fligner–Policello test
- Brunner–Munzel test

### 4.5 Tests of categorical data
- Chi-square goodness-of-fit test
- Chi-square test of independence
- Chi-square test of homogeneity
- Fisher's exact test
- McNemar's test
- Cochran's Q test
- Binomial test
- Multinomial test
- One-proportion z-test
- Two-proportion z-test
- Exact tests for contingency tables
- Mantel–Haenszel test

### 4.6 Correlation and association inference
- Pearson correlation significance test
- Spearman correlation significance test
- Kendall's tau significance test
- Partial correlation test
- Semi-partial correlation
- Point-biserial correlation test
- Rank correlation tests
- Tests for equality of correlation coefficients

### 4.7 Goodness-of-fit and distribution tests
- Chi-square goodness-of-fit
- Kolmogorov–Smirnov test
- Shapiro–Wilk test
- Anderson–Darling test
- Cramér–von Mises test
- Jarque–Bera test
- Lilliefors test
- D'Agostino's K-squared test
- Levene's test
- Brown–Forsythe test
- Bartlett's test
- Fligner–Killeen test

---

# PART III: MODELLING AND ADVANCED INFERENCE

## 5. REGRESSION AND GENERALISED LINEAR MODELS

### 5.1 Linear regression
- Simple linear regression
- Multiple linear regression
- Polynomial regression
- Interaction regression
- Weighted least squares regression
- General least squares
- Generalised least squares
- Regression with categorical predictors
- Regression with continuous predictors
- Regression with dummy variables

### 5.2 Generalised linear models
- Generalised linear models
- Binary logistic regression
- Multinomial logistic regression
- Ordinal logistic regression
- Poisson regression
- Negative binomial regression
- Quasi-Poisson regression
- Gamma regression
- Inverse Gaussian regression
- Probit regression
- Complementary log-log regression
- Zero-inflated Poisson regression
- Zero-inflated negative binomial regression
- Hurdle models

### 5.3 Advanced regression
- Robust regression
- Quantile regression
- Ridge regression
- Lasso regression
- Elastic net regression
- Generalised additive models
- Non-linear regression
- Spline regression
- Mixed-effects regression
- Multilevel regression
- Hierarchical regression
- Bayesian regression
- Penalised regression

### 5.4 Regression diagnostics
- Residual analysis
- Linearity assessment
- Heteroscedasticity testing
- Multicollinearity assessment
- Autocorrelation testing
- Influence diagnostics
- Leverage analysis
- Cook's distance
- DFBETAs
- Model specification tests
- Goodness-of-fit assessment
- Cross-validation

---

## 6. BAYESIAN STATISTICS

### 6.1 Bayesian foundations
- Prior distributions
- Likelihood functions
- Posterior distributions
- Posterior predictive distributions
- Bayes' theorem
- Posterior odds
- Bayes factors
- Bayesian decision theory

### 6.2 Bayesian estimation
- Bayesian point estimation
- Bayesian interval estimation
- Credible intervals
- Highest posterior density intervals
- Conjugate prior analysis
- Empirical Bayes estimation
- Hierarchical Bayesian estimation
- Bayesian model averaging

### 6.3 Bayesian hypothesis testing
- Bayesian hypothesis comparison
- Bayes factors
- Posterior probability of hypotheses
- Bayesian evidence assessment
- Bayesian equivalence testing

### 6.4 Bayesian computational methods
- Markov Chain Monte Carlo
- Metropolis–Hastings algorithm
- Gibbs sampling
- Hamiltonian Monte Carlo
- No-U-Turn Sampler
- Importance sampling
- Sequential Monte Carlo
- Variational inference
- Approximate Bayesian computation
- Posterior predictive checking
- Convergence diagnostics

### 6.5 Bayesian modelling
- Bayesian linear regression
- Bayesian logistic regression
- Bayesian ANOVA
- Bayesian hierarchical models
- Bayesian multilevel models
- Bayesian survival models
- Bayesian time-series models
- Bayesian spatial models
- Bayesian networks
- Bayesian non-parametric models

---

## 7. EXPERIMENTAL DESIGN AND DESIGN OF EXPERIMENTS

### 7.1 Principles of experimental design
- Randomisation
- Replication
- Blocking
- Factorial experimentation
- Control groups
- Treatment allocation
- Experimental units
- Confounding control

### 7.2 Classical experimental designs
- Completely randomised design
- Randomised complete block design
- Latin square design
- Graeco-Latin square design
- Factorial design
- Full factorial design
- Fractional factorial design
- Split-plot design
- Split-split-plot design
- Nested design
- Repeated-measures design
- Crossover design

### 7.3 Advanced experimental designs
- Response surface methodology
- Central composite design
- Box–Behnken design
- Mixture design
- Optimal design
- D-optimal design
- A-optimal design
- G-optimal design
- Taguchi methods
- Robust parameter design
- Sequential experimental design
- Adaptive experimentation

### 7.4 Clinical and intervention designs
- Parallel-group trials
- Cluster-randomised trials
- Crossover trials
- Factorial clinical trials
- Stepped-wedge trials
- Adaptive clinical trials
- Non-inferiority trials
- Equivalence trials
- Superiority trials
- Single-arm trials

### 7.5 Experimental analysis
- Treatment-effect estimation
- Analysis of variance
- Blocking analysis
- Factorial effect analysis
- Interaction analysis
- Response surface analysis
- Sample-size determination
- Power analysis
- Interim analysis
- Multiple-comparison procedures

---

## 8. SAMPLING AND SURVEY STATISTICS

### 8.1 Probability sampling
- Simple random sampling
- Systematic sampling
- Stratified random sampling
- Cluster sampling
- Multistage sampling
- Multiphase sampling
- Probability proportional to size sampling
- Unequal probability sampling
- Two-stage sampling
- Area sampling

### 8.2 Non-probability sampling
- Convenience sampling
- Purposive sampling
- Quota sampling
- Snowball sampling
- Respondent-driven sampling
- Consecutive sampling
- Volunteer sampling

### 8.3 Survey estimation
- Population mean estimation
- Population total estimation
- Population proportion estimation
- Ratio estimation
- Regression estimation
- Calibration estimation
- Horvitz–Thompson estimation
- Generalised regression estimation

### 8.4 Complex survey analysis
- Survey weights
- Sampling weights
- Non-response adjustment
- Post-stratification
- Raking
- Finite population correction
- Design effects
- Taylor series linearisation
- Replicate-weight variance estimation
- Jackknife variance estimation
- Balanced repeated replication
- Bootstrap survey variance estimation
- Complex-survey regression
- Complex-survey hypothesis testing

### 8.5 Sample-size determination
- Estimation-based sample size
- Hypothesis-testing sample size
- Power-based sample size
- Finite population sample size
- Cluster-adjusted sample size
- Design-effect-adjusted sample size
- Non-response-adjusted sample size
- Precision-based sample size

---

## 9. MULTIVARIATE STATISTICS

### 9.1 Dimension reduction
- Principal component analysis
- Exploratory factor analysis
- Confirmatory factor analysis
- Independent component analysis
- Correspondence analysis
- Multiple correspondence analysis
- Multidimensional scaling
- Non-negative matrix factorisation

### 9.2 Multivariate association
- Canonical correlation analysis
- Partial least squares
- Multivariate regression
- Multivariate analysis of variance
- Multivariate analysis of covariance

### 9.3 Classification and discrimination
- Linear discriminant analysis
- Quadratic discriminant analysis
- Classification analysis
- Mahalanobis distance
- Canonical discriminant analysis

### 9.4 Clustering
- K-means clustering
- K-medoids clustering
- Hierarchical clustering
- Agglomerative clustering
- Divisive clustering
- Model-based clustering
- Gaussian mixture models
- Fuzzy clustering
- Density-based clustering
- DBSCAN
- Spectral clustering

---

## 10. NON-PARAMETRIC AND DISTRIBUTION-FREE STATISTICS

- Sign test
- Wilcoxon signed-rank test
- Mann–Whitney U test
- Kruskal–Wallis test
- Friedman test
- Spearman correlation
- Kendall correlation
- Permutation tests
- Randomisation tests
- Bootstrap inference
- Kernel density estimation
- Non-parametric regression
- Local polynomial regression
- Smoothing splines
- Quantile-based inference
- Distribution-free confidence intervals

---

## 11. TIME-SERIES AND FORECASTING

### 11.1 Time-series exploration
- Trend analysis
- Seasonal analysis
- Cyclical analysis
- Autocorrelation
- Partial autocorrelation
- Decomposition
- Moving averages
- Exponential smoothing
- Structural-break analysis

### 11.2 Stationarity and diagnostics
- Augmented Dickey–Fuller test
- Phillips–Perron test
- KPSS test
- Ljung–Box test
- Box–Pierce test
- Unit-root testing
- Residual diagnostics

### 11.3 Time-series models
- Autoregressive models
- Moving-average models
- ARMA
- ARIMA
- Seasonal ARIMA
- Vector autoregression
- Vector error-correction models
- ARCH
- GARCH
- State-space models
- Structural time-series models
- Dynamic factor models
- Regime-switching models

### 11.4 Forecasting
- Naive forecasting
- Seasonal naive forecasting
- Exponential smoothing
- Holt's method
- Holt–Winters method
- ARIMA forecasting
- Regression-based forecasting
- Probabilistic forecasting
- Forecast intervals
- Forecast accuracy assessment

---

## 12. SURVIVAL AND EVENT-HISTORY ANALYSIS

- Kaplan–Meier estimator
- Nelson–Aalen estimator
- Life-table analysis
- Log-rank test
- Wilcoxon–Breslow–Gehan test
- Cox proportional hazards regression
- Stratified Cox regression
- Time-dependent Cox regression
- Parametric survival regression
- Weibull survival models
- Exponential survival models
- Log-normal survival models
- Accelerated failure-time models
- Competing-risks analysis
- Fine–Gray regression
- Recurrent-event analysis
- Frailty models
- Multi-state models
- Restricted mean survival time
- Hazard ratio estimation
- Survival probability estimation

---

## 13. SPATIAL STATISTICS AND GEOSTATISTICS

### 13.1 Spatial exploration
- Spatial distribution analysis
- Spatial point-pattern analysis
- Spatial clustering
- Spatial density estimation
- Kernel density mapping
- Spatial autocorrelation

### 13.2 Spatial dependence
- Global Moran's I
- Local Moran's I
- Geary's C
- Getis–Ord Gi*
- Spatial correlograms

### 13.3 Spatial modelling
- Spatial autoregressive models
- Spatial error models
- Spatial Durbin models
- Conditional autoregressive models
- Simultaneous autoregressive models
- Spatial generalised linear mixed models
- Spatial Bayesian models
- Geographically weighted regression
- Spatial panel models

### 13.4 Geostatistics
- Variograms
- Semivariograms
- Kriging
- Ordinary kriging
- Universal kriging
- Co-kriging
- Spatial interpolation
- Gaussian processes

---

## 14. CAUSAL INFERENCE

### 14.1 Causal foundations
- Potential outcomes framework
- Counterfactual inference
- Directed acyclic graphs
- Confounding assessment
- Identification assumptions
- Average treatment effect
- Average treatment effect on the treated
- Average treatment effect on the untreated
- Heterogeneous treatment effects

### 14.2 Experimental causal methods
- Randomised controlled trials
- Cluster-randomised experiments
- Factorial experiments
- Instrumented randomisation

### 14.3 Observational causal methods
- Propensity-score matching
- Propensity-score weighting
- Inverse probability weighting
- Regression adjustment
- Doubly robust estimation
- Difference-in-differences
- Instrumental-variable estimation
- Regression discontinuity design
- Synthetic control
- Interrupted time-series analysis
- Matching methods
- Mediation analysis
- Moderation analysis
- Sensitivity analysis for unmeasured confounding
- Targeted maximum likelihood estimation

---

# PART IV: SPECIALISED STATISTICAL DISCIPLINES

## 15. STOCHASTIC PROCESSES

- Markov chains
- Markov processes
- Continuous-time Markov chains
- Discrete-time Markov chains
- Poisson processes
- Renewal processes
- Birth–death processes
- Branching processes
- Brownian motion
- Wiener processes
- Random walks
- Martingales
- Gaussian processes
- Stochastic differential equations
- Queueing theory
- Reliability stochastic processes

## 16. RELIABILITY AND QUALITY STATISTICS

### 16.1 Reliability analysis
- Reliability functions
- Failure-time distributions
- Mean time to failure
- Mean time between failures
- Hazard functions
- System reliability
- Series-system reliability
- Parallel-system reliability
- Accelerated life testing
- Reliability growth modelling
- Repairable-system analysis

### 16.2 Statistical quality control
- Statistical process control
- Shewhart control charts
- X-bar charts
- R charts
- S charts
- p charts
- np charts
- c charts
- u charts
- CUSUM charts
- EWMA charts
- Process capability analysis
- Process performance analysis
- Acceptance sampling
- Six Sigma statistical methods

## 17. EPIDEMIOLOGICAL AND BIOSTATISTICAL METHODS

### 17.1 Disease frequency
- Incidence
- Incidence rate
- Cumulative incidence
- Prevalence
- Point prevalence
- Period prevalence
- Mortality rate
- Case-fatality proportion
- Standardised mortality ratios

### 17.2 Measures of association and impact
- Risk ratio
- Rate ratio
- Odds ratio
- Prevalence ratio
- Risk difference
- Attributable risk
- Population attributable fraction
- Number needed to treat
- Number needed to harm

### 17.3 Epidemiological analysis
- Cohort analysis
- Case-control analysis
- Cross-sectional analysis
- Ecological analysis
- Outbreak analysis
- Stratified analysis
- Direct standardisation
- Indirect standardisation
- Mantel–Haenszel analysis
- Diagnostic test accuracy
- Sensitivity and specificity
- Positive and negative predictive values
- Likelihood ratios
- ROC curve analysis
- Meta-analysis of epidemiological studies

### 17.4 Clinical and biomedical statistics
- Clinical trial analysis
- Repeated-measures biomedical analysis
- Diagnostic accuracy studies
- Agreement analysis
- Bland–Altman analysis
- Bioequivalence analysis
- Dose-response modelling
- Pharmacokinetic modelling
- Pharmacodynamic modelling
- Longitudinal clinical analysis

## 18. PSYCHOMETRICS AND MEASUREMENT THEORY

- Classical test theory
- Item response theory
- Rasch measurement models
- Reliability analysis
- Cronbach's alpha
- McDonald's omega
- Split-half reliability
- Test–retest reliability
- Inter-rater reliability
- Intraclass correlation coefficient
- Measurement validity
- Construct validity
- Convergent validity
- Discriminant validity
- Exploratory factor analysis
- Confirmatory factor analysis
- Measurement invariance
- Differential item functioning
- Scale development
- Item analysis
- Generalisability theory

## 19. STATISTICAL LEARNING AND PREDICTIVE MODELLING

### 19.1 Supervised learning
- Linear regression
- Logistic regression
- Decision trees
- Random forests
- Gradient boosting
- Extreme gradient boosting
- Support vector machines
- K-nearest neighbours
- Naive Bayes
- Classification algorithms
- Regression algorithms

### 19.2 Unsupervised learning
- Clustering
- Dimension reduction
- Principal component analysis
- Factor analysis
- Anomaly detection
- Association-rule mining
- Density estimation

### 19.3 Model evaluation
- Train-test splitting
- Cross-validation
- Bootstrap validation
- Confusion matrix
- Accuracy
- Precision
- Recall
- Specificity
- F1 score
- ROC curve
- Area under the ROC curve
- Precision–recall curve
- Calibration analysis
- Brier score
- Regression prediction errors
- Bias–variance assessment

### 19.4 Advanced learning methods
- Regularisation
- Ensemble learning
- Stacking
- Bagging
- Boosting
- Feature selection
- Feature importance
- Model interpretability
- Partial dependence
- SHAP analysis
- Survival machine learning
- Imbalanced classification methods

---

# PART V: CROSS-CUTTING STATISTICAL CAPABILITIES

## 20. EFFECT-SIZE ESTIMATION

Effect sizes should be available as method-specific reporting components.

- Cohen's d
- Hedges' g
- Glass's delta
- Eta-squared
- Partial eta-squared
- Omega-squared
- Cohen's f
- Cramér's V
- Phi coefficient
- Pearson's r
- Rank-biserial correlation
- Common-language effect size
- Odds ratio
- Risk ratio
- Risk difference
- Incidence-rate ratio
- Regression coefficients
- Standardised regression coefficients
- R-squared
- Adjusted R-squared
- Partial R-squared
- Hazard ratio
- Number needed to treat
- Number needed to harm

## 21. ASSUMPTION TESTING AND STATISTICAL DIAGNOSTICS

### 21.1 Distributional diagnostics
- Shapiro–Wilk test
- Anderson–Darling test
- Kolmogorov–Smirnov test
- Lilliefors test
- Jarque–Bera test
- Q–Q plot assessment
- P–P plot assessment

### 21.2 Variance and dependence diagnostics
- Levene's test
- Brown–Forsythe test
- Bartlett's test
- Fligner–Killeen test
- Durbin–Watson test
- Breusch–Pagan test
- White's test
- Breusch–Godfrey test

### 21.3 Regression diagnostics
- Variance inflation factor
- Tolerance
- Residual analysis
- Cook's distance
- Leverage
- DFBETAs
- DFFITS
- Ramsey RESET test
- Influence analysis
- Specification diagnostics

### 21.4 General data diagnostics
- Missing-data analysis
- Missing completely at random assessment
- Missing at random assessment
- Missing not at random assessment
- Outlier detection
- Duplicate detection
- Data consistency checks
- Data validity checks
- Distributional anomaly detection

## 22. RESAMPLING, SIMULATION AND COMPUTATIONAL INFERENCE

- Bootstrap
- Parametric bootstrap
- Non-parametric bootstrap
- Cluster bootstrap
- Block bootstrap
- Permutation testing
- Randomisation inference
- Monte Carlo simulation
- Markov Chain Monte Carlo
- Importance sampling
- Rejection sampling
- Sequential Monte Carlo
- Numerical integration
- Numerical optimisation
- Simulation-based power analysis
- Statistical uncertainty propagation

## 23. META-ANALYSIS AND EVIDENCE SYNTHESIS

- Fixed-effect meta-analysis
- Random-effects meta-analysis
- Multilevel meta-analysis
- Network meta-analysis
- Pairwise meta-analysis
- Proportional meta-analysis
- Meta-regression
- Heterogeneity analysis
- Cochran's Q
- I-squared statistic
- Tau-squared
- Publication-bias assessment
- Funnel plots
- Egger's test
- Trim-and-fill method
- Leave-one-out sensitivity analysis
- Cumulative meta-analysis
- Individual participant data meta-analysis
- Systematic-review statistical synthesis

## 24. MISSING-DATA STATISTICS

- Complete-case analysis
- Available-case analysis
- Mean imputation
- Regression imputation
- Hot-deck imputation
- Multiple imputation
- Multiple imputation by chained equations
- Joint-model multiple imputation
- Inverse probability weighting for missingness
- Maximum likelihood estimation with missing data
- Sensitivity analysis for missing-not-at-random mechanisms

---

# PART VI: SHARED SOFTWARE AND REPORTING FRAMEWORK

## 25. STATISTICAL REPORTING

Every applicable analysis should support structured reporting of:

- Research objective
- Research question
- Statistical branch and domain
- Selected method
- Method-selection rationale
- Variable roles and measurement scales
- Hypotheses, where applicable
- Sample size and analytical sample
- Test statistic or model estimates
- Degrees of freedom, where applicable
- P-value, where applicable
- Confidence interval or credible interval, where applicable
- Effect size, where applicable
- Assumption checks
- Model diagnostics
- Missing-data handling
- Limitations
- Interpretation
- Reproducibility information

## 26. VISUALISATION AND PRESENTATION

TimanStat should support:

- Descriptive charts
- Inferential plots
- Confidence-interval plots
- Forest plots
- Regression diagnostic plots
- Residual plots
- Survival curves
- Kaplan–Meier plots
- ROC curves
- Precision–recall curves
- Calibration plots
- Partial dependence plots
- Spatial maps
- Time-series plots
- Forecast plots
- Control charts
- Meta-analysis funnel plots
- Effect-size plots

## 27. STATISTICAL METHOD METADATA

Every catalogue method should have a standard machine-readable record containing:

1. `method_id` — unique method identifier.
2. `name` — human-readable method name.
3. `domain` — primary statistical domain.
4. `branch` — descriptive, inferential, foundational, predictive or other applicable classification.
5. `family` — method family.
6. `description` — methodological purpose.
7. `research_objectives` — questions the method addresses.
8. `variable_requirements` — outcome, predictors, factors and measurement types.
9. `data_requirements` — required data structure.
10. `assumptions` — method-specific assumptions.
11. `selection_rules` — conditions for recommending the method.
12. `outputs` — statistics, estimates and model outputs.
13. `effect_sizes` — applicable effect-size measures.
14. `interval_estimates` — applicable confidence or credible intervals.
15. `diagnostics` — applicable diagnostic procedures.
16. `alternatives` — related methods and alternatives.
17. `limitations` — known methodological limitations.
18. `tags` — secondary domains and cross-classification.
19. `implementation_status` — development state.
20. `references` — authoritative methodological references.

## 28. IMPLEMENTATION STATUS

Catalogue inclusion and implementation status must remain separate.

Permitted statuses:

- `planned`
- `in_development`
- `implemented`
- `tested`
- `validated`

A method must not be represented as operational merely because it is registered in the catalogue.

## 29. ARCHITECTURAL PRINCIPLES

1. The catalogue must be comprehensive and extensible.
2. Every method must have a unique identifier.
3. Each method must have one primary domain and may have multiple secondary tags.
4. Related methods must be grouped into families.
5. Statistical selection must consider the research objective, data structure, variable types, sampling design and assumptions.
6. The catalogue must distinguish descriptive summaries from inferential procedures.
7. Probability theory and computational methods must be represented as foundational or supporting domains rather than forced into the two-branch classification.
8. Statistical calculations must be separated from method selection and reporting.
9. Effect sizes, uncertainty estimates and diagnostics must be method-specific.
10. No method should be represented as implemented without working, tested and validated computation.
11. The framework must support future statistical disciplines without restructuring the core architecture.

## 30. FUTURE EXTENSIBILITY

The taxonomy must allow new statistical disciplines, methods and computational approaches to be registered without redesigning the core catalogue.

Potential extensions include advanced functional data analysis, compositional data analysis, extreme-value statistics, directional statistics, mathematical statistics, information theory, network statistics, spatial-temporal modelling, causal machine learning and advanced statistical decision theory.

**End of catalogue.**
