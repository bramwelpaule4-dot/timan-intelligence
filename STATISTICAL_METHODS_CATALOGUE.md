# TIMANSTAT STATISTICAL METHODS CATALOGUE

**Version:** 2.1  
**Status:** Revised comprehensive statistical knowledge blueprint  
**Product:** TimanStat  
**Organisation:** Timan Analytics  
**Supersedes:** Version 2.0

---

# 1. PURPOSE AND SCOPE

## 1.1 Purpose

This catalogue defines the statistical knowledge, methods, models, research designs, computational procedures, diagnostics and reporting capabilities that TimanStat should recognise and progressively support.

TimanStat is intended to serve as a general statistical analysis platform for research and applied work across:

- General quantitative research
- Mathematics and mathematical statistics
- Biostatistics and biomedical research
- Epidemiology and public health
- Agriculture and environmental sciences
- Economics and econometrics
- Education and social sciences
- Business and management
- Psychology and measurement
- Engineering and quality control
- Government, development and humanitarian programming

The catalogue is a knowledge blueprint, not an implementation claim. Inclusion of an item does not mean that TimanStat can currently execute it.

## 1.2 Core objectives

TimanStat should progressively be able to:

1. Understand a user's research objective or analytical question.
2. Identify the relevant statistical purpose and knowledge area.
3. Inspect the dataset's structure, variables, measurement scales and quality.
4. Identify suitable statistical methods and explain their selection.
5. Identify the target quantity or estimand where applicable.
6. Specify the statistical model or analytical procedure.
7. Check whether the data and study design support the proposed analysis.
8. Evaluate relevant assumptions and diagnostics.
9. Execute validated statistical computations.
10. Interpret results, uncertainty and limitations.
11. Produce appropriate tables, visualisations and reports.
12. Explain when a proposed analysis is unsuitable or unsupported.

## 1.3 Scope and classification principle

The catalogue distinguishes seven different kinds of statistical knowledge:

- **Statistical purposes:** what the analysis is intended to accomplish.
- **Knowledge areas:** the broad disciplines and bodies of statistical theory.
- **Method families:** groups of related analytical procedures.
- **Statistical entities:** methods, models, designs, diagnostics, algorithms, measures and visualisations.
- **Inference paradigms:** approaches such as frequentist, Bayesian and randomisation-based inference.
- **Application domains:** fields in which statistical methods are used.
- **Computational procedures:** numerical and algorithmic techniques used to obtain results.

These dimensions are related but must not be collapsed into a single classification.

---

# PART I — STATISTICAL PURPOSES AND FOUNDATIONS

# 2. STATISTICAL PURPOSES

Statistical purpose describes the principal objective of an analysis. A method may serve more than one purpose depending on how it is used.

## 2.1 Descriptive statistics

Organises, summarises and presents observed data.

Typical questions:
- What does the observed dataset contain?
- What is the distribution of a variable?
- What are the characteristics of the study population or sample?
- How do observed groups differ?

## 2.2 Inferential statistics

Uses sample information and a statistical model or sampling framework to make statements about a broader population or data-generating process.

Typical questions:
- Is there evidence of a population difference?
- What is the uncertainty around an estimate?
- Is an observed association compatible with a specified null hypothesis?
- What population parameter can be estimated from the sample?

## 2.3 Predictive statistics

Uses observed information to predict unknown or future outcomes.

Typical questions:
- What outcome is expected for a new observation?
- Which individuals or units are at higher predicted risk?
- How accurately can future values be forecast?

## 2.4 Causal analysis

Estimates or evaluates the effects of interventions, exposures or treatments under explicit causal assumptions.

Typical questions:
- What is the effect of an intervention?
- What would have happened to the same population under an alternative exposure?
- Which causal pathways may explain an observed effect?

## 2.5 Exploratory analysis

Investigates data structure, patterns, anomalies, relationships and possible hypotheses without necessarily beginning with a formal confirmatory hypothesis.

## 2.6 Decision and optimisation analysis

Uses statistical estimates, uncertainty and decision criteria to support choices, resource allocation, treatment decisions or operational optimisation.

**Classification rule:** Descriptive and inferential statistics remain fundamental analytical purposes, but predictive, causal, exploratory and decision-oriented analyses must also be represented. Not every statistical discipline belongs exclusively to one purpose.

---

# 3. PROBABILITY THEORY AND DISTRIBUTIONS

Probability theory provides the mathematical foundation for statistical modelling and inference.

## 3.1 Probability fundamentals

- Classical probability
- Empirical probability
- Axiomatic probability
- Conditional probability
- Joint probability
- Marginal probability
- Independence of events
- Conditional independence
- Mutually exclusive events
- Bayes' theorem
- Law of total probability
- Combinatorics
- Permutations and combinations
- Inclusion–exclusion principle

## 3.2 Random variables and distributions

- Discrete random variables
- Continuous random variables
- Mixed random variables
- Probability mass functions
- Probability density functions
- Cumulative distribution functions
- Joint distributions
- Marginal distributions
- Conditional distributions
- Transformations of random variables
- Order statistics
- Quantile functions

## 3.3 Probability moments and properties

- Mathematical expectation
- Variance
- Standard deviation
- Covariance
- Correlation
- Conditional expectation
- Conditional variance
- Moment-generating functions
- Characteristic functions
- Probability-generating functions
- Higher-order moments
- Skewness
- Kurtosis

## 3.4 Discrete probability distributions

- Bernoulli
- Binomial
- Geometric
- Negative binomial
- Hypergeometric
- Poisson
- Discrete uniform
- Multinomial
- Beta-binomial
- Zero-truncated count distributions
- Conway–Maxwell–Poisson

## 3.5 Continuous probability distributions

- Uniform
- Normal
- Standard normal
- Exponential
- Gamma
- Beta
- Chi-square
- Student's t
- F
- Weibull
- Log-normal
- Logistic
- Cauchy
- Pareto
- Laplace
- Rayleigh
- Gumbel
- Inverse Gaussian
- Generalised extreme-value
- Generalised Pareto
- Multivariate normal
- Multivariate t
- Dirichlet
- Wishart
- Inverse-Wishart
- von Mises
- Other directional distributions

## 3.6 Sampling distributions and limit theorems

- Sampling distributions
- Sampling distribution of the mean
- Sampling distribution of a proportion
- Sampling distribution of variance
- Standard error distributions
- Central Limit Theorem
- Weak Law of Large Numbers
- Strong Law of Large Numbers
- Slutsky's theorem
- Delta method
- Continuous mapping theorem
- Asymptotic normality
- Order-statistic distributions

---

# PART II — DESCRIPTIVE STATISTICS AND EXPLORATORY ANALYSIS

# 4. DESCRIPTIVE STATISTICS

Descriptive statistics organise, summarise and present observed data. They do not, by themselves, establish population-level statistical significance or causation.

## 4.1 Frequency and distribution analysis

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
- Conditional frequency distributions
- Weighted frequencies

## 4.2 Measures of central tendency

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
- Geometric and harmonic summaries where appropriate

## 4.3 Measures of dispersion

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
- Robust dispersion measures

## 4.4 Measures of position

- Quartiles
- Deciles
- Percentiles
- Quantiles
- Quintiles
- Z-scores
- Standard scores
- Percentile ranks
- Rank statistics
- Standardised values

## 4.5 Measures of distribution shape

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
- Tail weight
- Empirical distribution shape

## 4.6 Descriptive association and relationship measures

- Covariance
- Pearson correlation coefficient
- Spearman rank correlation coefficient
- Kendall's tau
- Phi coefficient
- Cramér's V
- Contingency coefficient
- Point-biserial correlation coefficient
- Rank-biserial correlation coefficient
- Correlation ratios
- Distance correlation
- Mutual information
- Theil's U

A descriptive association coefficient summarises the observed data. Its confidence interval or significance test is a separate inferential procedure.

## 4.7 Graphical descriptive methods

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
- Ridgeline plot
- Hexbin plot
- Pair plot
- Correlogram

## 4.8 Exploratory data analysis

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
- Pattern and anomaly exploration
- Data transformation exploration
- Preliminary relationship assessment

---

# PART III — CLASSICAL AND BAYESIAN INFERENCE

# 5. CLASSICAL AND FREQUENTIST INFERENCE

Frequentist inference evaluates procedures through their repeated-sampling properties. It includes estimation, confidence intervals, hypothesis testing and model-based inference.

## 5.1 Statistical estimation

- Point estimation
- Interval estimation
- Method of moments estimation
- Maximum likelihood estimation
- Least squares estimation
- Generalised least squares estimation
- Minimum variance estimation
- Unbiased estimation
- Consistent estimation
- Efficient estimation
- Sufficient statistics
- Complete statistics
- Fisher information
- Standard errors
- Margin of error
- Profile likelihood estimation
- Restricted maximum likelihood
- Generalised method of moments

## 5.2 Confidence intervals

- Confidence interval for a population mean
- Confidence interval for a population proportion
- Confidence interval for a variance
- Confidence interval for a difference between means
- Confidence interval for a difference between proportions
- Confidence interval for correlation
- Confidence interval for regression coefficients
- Confidence interval for odds ratios
- Confidence interval for risk ratios
- Confidence interval for rate ratios
- Confidence interval for hazard ratios
- Confidence interval for effect sizes
- Bootstrap confidence intervals
- Profile likelihood confidence intervals
- Exact confidence intervals
- Simultaneous confidence intervals
- Prediction intervals
- Tolerance intervals

## 5.3 Hypothesis testing

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
- Benjamini–Yekutieli procedure
- Permutation-based tests
- Equivalence testing
- Non-inferiority testing
- Sequential testing

## 5.4 Tests of means and differences

**Parametric procedures**

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
- Planned contrasts
- Post-hoc comparisons
- Multiple-comparison procedures

**Non-parametric or distribution-free procedures**

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

The catalogue must distinguish a test's mathematical assumptions from the simplistic label "parametric" or "non-parametric". For example, rank tests may target different distributional quantities from tests of means.

## 5.5 Tests of categorical data

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
- Tests for paired categorical data
- Tests for trend in proportions
- Exact conditional tests

## 5.6 Correlation and association inference

- Pearson correlation significance test
- Spearman correlation significance test
- Kendall's tau significance test
- Partial correlation test
- Semi-partial correlation inference
- Point-biserial correlation test
- Rank correlation tests
- Tests for equality of correlation coefficients
- Confidence intervals for association measures
- Tests of association in contingency tables

## 5.7 Goodness-of-fit and distribution tests

- Chi-square goodness-of-fit test
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

These tests must be classified as inferential procedures or diagnostics according to their actual role. Graphical assessments such as Q–Q plots are diagnostic visualisations, not hypothesis tests.

---

# 6. BAYESIAN STATISTICS

Bayesian statistics is a first-class inference paradigm and knowledge area. It must not be treated merely as a collection of separate regression methods.

## 6.1 Bayesian foundations

- Prior distributions
- Likelihood functions
- Posterior distributions
- Posterior predictive distributions
- Bayes' theorem
- Posterior odds
- Bayes factors
- Bayesian decision theory
- Prior elicitation
- Prior sensitivity analysis
- Exchangeability
- Hierarchical probability models

## 6.2 Bayesian estimation

- Bayesian point estimation
- Bayesian interval estimation
- Credible intervals
- Highest posterior density intervals
- Conjugate prior analysis
- Empirical Bayes estimation
- Hierarchical Bayesian estimation
- Bayesian model averaging
- Posterior summaries
- Posterior predictive estimation

## 6.3 Bayesian hypothesis evaluation

- Bayesian hypothesis comparison
- Bayes factors
- Posterior probability of hypotheses
- Bayesian evidence assessment
- Bayesian equivalence testing
- Bayesian decision rules
- Region of practical equivalence

## 6.4 Bayesian computational methods

- Markov Chain Monte Carlo
- Metropolis–Hastings algorithm
- Gibbs sampling
- Hamiltonian Monte Carlo
- No-U-Turn Sampler
- Importance sampling
- Rejection sampling
- Sequential Monte Carlo
- Variational inference
- Approximate Bayesian computation
- Posterior predictive checking
- Convergence diagnostics
- Effective sample size
- Monte Carlo standard error

## 6.5 Bayesian modelling

- Bayesian linear regression
- Bayesian logistic regression
- Bayesian generalised linear models
- Bayesian ANOVA
- Bayesian hierarchical models
- Bayesian multilevel models
- Bayesian survival models
- Bayesian time-series models
- Bayesian spatial models
- Bayesian networks
- Bayesian non-parametric models
- Bayesian mixture models
- Bayesian latent-variable models
- Bayesian causal models

---

# PART IV — MODELLING AND REGRESSION

# 7. REGRESSION AND GENERALISED LINEAR MODELS

## 7.1 Linear regression

- Simple linear regression
- Multiple linear regression
- Polynomial regression
- Interaction regression
- Weighted least squares regression
- Generalised least squares
- Regression with categorical predictors
- Regression with continuous predictors
- Regression with dummy variables
- Regression with transformed variables
- Restricted and constrained regression

## 7.2 Generalised linear models

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
- Beta regression
- Fractional response models

## 7.3 Advanced regression

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
- Partial least squares regression
- Reduced-rank regression
- Tobit regression
- Truncated regression
- Censored regression
- Multivariate regression
- Distributional regression

## 7.4 Longitudinal and clustered-data models

- Linear mixed-effects models
- Generalised linear mixed models
- Random-intercept models
- Random-slope models
- Growth-curve models
- Population-averaged models
- Generalised estimating equations
- Repeated-measures regression
- Clustered-data regression
- Hierarchical longitudinal models

## 7.5 Categorical response models

- Binary response models
- Multinomial response models
- Ordinal response models
- Adjacent-category models
- Continuation-ratio models
- Cumulative link models
- Log-linear models
- Multinomial probit models
- Ordinal probit models

## 7.6 Regression diagnostics and model evaluation

- Residual analysis
- Linearity assessment
- Heteroscedasticity testing
- Multicollinearity assessment
- Autocorrelation testing
- Influence diagnostics
- Leverage analysis
- Cook's distance
- DFBETAs
- DFFITS
- Model specification tests
- Goodness-of-fit assessment
- Calibration assessment
- Residual distribution assessment
- Cross-validation
- External validation

Cross-validation and external validation are model-evaluation procedures. They should not be conflated with residual diagnostics or assumption tests.

---

# PART V — STUDY DESIGN, SAMPLING AND SURVEY STATISTICS

# 8. EXPERIMENTAL DESIGN AND DESIGN OF EXPERIMENTS

Experimental design is a distinct design domain. A design specifies how observations, treatments and experimental units are organised; a statistical analysis method is selected to analyse the resulting data.

## 8.1 Principles of experimental design

- Randomisation
- Replication
- Blocking
- Factorial experimentation
- Control groups
- Treatment allocation
- Experimental units
- Confounding control
- Allocation concealment
- Blinding
- Internal validity
- External validity

## 8.2 Classical experimental designs

- Completely randomised design
- Randomised complete block design
- Latin square design
- Graeco-Latin square design
- Full factorial design
- Fractional factorial design
- Split-plot design
- Split-split-plot design
- Nested design
- Repeated-measures design
- Crossover design
- Incomplete block design
- Balanced incomplete block design

## 8.3 Advanced experimental designs

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
- Factor screening
- Definitive screening designs

## 8.4 Clinical and intervention study designs

- Parallel-group trials
- Individually randomised trials
- Cluster-randomised trials
- Crossover trials
- Factorial clinical trials
- Stepped-wedge trials
- Adaptive clinical trials
- Non-inferiority trials
- Equivalence trials
- Superiority trials
- Single-arm trials
- Pragmatic trials
- Explanatory trials
- Platform trials
- Basket trials
- Umbrella trials

## 8.5 Experimental analysis procedures

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
- Intention-to-treat analysis
- Per-protocol analysis
- Sensitivity analysis

## 8.6 Design-to-analysis relationships

TimanStat should link each design structure to appropriate analysis options. For example:

- Randomised complete block design → blocked ANOVA or an appropriate mixed model.
- Cluster-randomised trial → cluster-aware regression, mixed models or GEE.
- Crossover trial → paired or period-aware models, with carryover considerations.
- Repeated-measures design → repeated-measures ANOVA or longitudinal models.
- Factorial design → main-effect and interaction models.

These are examples of relationships, not automatic one-to-one rules. The actual analysis depends on the outcome, allocation, number of factors, dependence structure and estimand.

---

# 9. SAMPLING AND SURVEY STATISTICS

## 9.1 Probability sampling

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
- Adaptive cluster sampling

## 9.2 Non-probability sampling

- Convenience sampling
- Purposive sampling
- Quota sampling
- Snowball sampling
- Respondent-driven sampling
- Consecutive sampling
- Volunteer sampling
- Time-location sampling

Non-probability samples do not automatically support design-based population inference. Model-based inference, weighting assumptions and generalisability must be considered separately.

## 9.3 Survey estimation

- Population mean estimation
- Population total estimation
- Population proportion estimation
- Ratio estimation
- Regression estimation
- Calibration estimation
- Horvitz–Thompson estimation
- Generalised regression estimation
- Domain estimation
- Small-area estimation

## 9.4 Complex survey analysis

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
- Survey design-based confidence intervals
- Non-response bias assessment

## 9.5 Sample-size determination

- Estimation-based sample size
- Hypothesis-testing sample size
- Power-based sample size
- Finite population sample size
- Cluster-adjusted sample size
- Design-effect-adjusted sample size
- Non-response-adjusted sample size
- Precision-based sample size
- Equivalence and non-inferiority sample size
- Diagnostic accuracy sample size
- Survival study sample size
- Simulation-based sample size

---

# PART VI — SPECIALISED STATISTICAL DISCIPLINES

# 10. MULTIVARIATE STATISTICS

## 10.1 Dimension reduction

- Principal component analysis
- Exploratory factor analysis
- Confirmatory factor analysis
- Independent component analysis
- Correspondence analysis
- Multiple correspondence analysis
- Multidimensional scaling
- Non-negative matrix factorisation
- Factor rotation
- Sparse principal component analysis

## 10.2 Multivariate association and modelling

- Canonical correlation analysis
- Partial least squares
- Multivariate regression
- Multivariate analysis of variance
- Multivariate analysis of covariance
- Multivariate analysis of repeated measures
- Canonical variate analysis
- Multivariate generalised linear models

## 10.3 Classification and discrimination

- Linear discriminant analysis
- Quadratic discriminant analysis
- Classification analysis
- Mahalanobis distance
- Canonical discriminant analysis
- Regularised discriminant analysis

## 10.4 Clustering

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
- Latent class analysis
- Latent profile analysis

---

# 11. NON-PARAMETRIC AND DISTRIBUTION-FREE STATISTICS

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
- Rank-based methods
- Empirical likelihood
- Non-parametric survival methods

This domain groups methods by their distributional framework. It does not create duplicate method records. A method listed elsewhere should have one canonical identity and be cross-referenced here.

---

# 12. TIME-SERIES AND FORECASTING

## 12.1 Time-series exploration

- Trend analysis
- Seasonal analysis
- Cyclical analysis
- Autocorrelation
- Partial autocorrelation
- Decomposition
- Moving averages
- Exponential smoothing
- Structural-break analysis
- Change-point detection

## 12.2 Stationarity and diagnostics

- Augmented Dickey–Fuller test
- Phillips–Perron test
- KPSS test
- Ljung–Box test
- Box–Pierce test
- Unit-root testing
- Residual diagnostics
- Seasonal unit-root testing
- Structural-break testing

## 12.3 Time-series models

- Autoregressive models
- Moving-average models
- ARMA
- ARIMA
- Seasonal ARIMA
- Vector autoregression
- Vector error-correction models
- ARCH
- GARCH
- EGARCH
- GJR-GARCH
- State-space models
- Structural time-series models
- Dynamic factor models
- Regime-switching models
- Fractional integration models
- Cointegration models
- Bayesian time-series models
- Functional time-series models

## 12.4 Forecasting

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
- Rolling-origin evaluation
- Forecast combination
- Hierarchical forecasting

## 12.5 Spectral and volatility analysis

- Spectral analysis
- Periodograms
- Fourier methods
- Wavelet analysis
- Volatility modelling
- ARCH-family models
- Stochastic volatility models

---

# 13. SURVIVAL AND EVENT-HISTORY ANALYSIS

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
- Log-logistic survival models
- Accelerated failure-time models
- Competing-risks analysis
- Cause-specific hazard models
- Fine–Gray regression
- Recurrent-event analysis
- Frailty models
- Multi-state models
- Restricted mean survival time
- Hazard ratio estimation
- Survival probability estimation
- Cure models
- Interval-censored survival analysis
- Flexible parametric survival models
- Bayesian survival models
- Survival machine learning

---

# 14. SPATIAL STATISTICS AND GEOSTATISTICS

## 14.1 Spatial exploration

- Spatial distribution analysis
- Spatial point-pattern analysis
- Spatial clustering
- Spatial density estimation
- Kernel density mapping
- Spatial autocorrelation
- Spatial heterogeneity assessment

## 14.2 Spatial dependence

- Global Moran's I
- Local Moran's I
- Geary's C
- Getis–Ord Gi*
- Spatial correlograms
- Join-count statistics

## 14.3 Spatial modelling

- Spatial autoregressive models
- Spatial error models
- Spatial Durbin models
- Conditional autoregressive models
- Simultaneous autoregressive models
- Spatial generalised linear mixed models
- Spatial Bayesian models
- Geographically weighted regression
- Spatial panel models
- Disease mapping
- Spatial point-process models
- Marked point-process models
- Spatial-temporal models

## 14.4 Geostatistics

- Variograms
- Semivariograms
- Kriging
- Ordinary kriging
- Universal kriging
- Co-kriging
- Spatial interpolation
- Gaussian processes
- Indicator kriging
- Conditional simulation

---

# 15. CAUSAL INFERENCE

## 15.1 Causal foundations

- Potential outcomes framework
- Counterfactual inference
- Directed acyclic graphs
- Structural causal models
- Confounding assessment
- Identification assumptions
- Consistency
- Exchangeability
- Positivity
- Average treatment effect
- Average treatment effect on the treated
- Average treatment effect on the untreated
- Conditional average treatment effects
- Heterogeneous treatment effects
- Causal estimands

## 15.2 Experimental causal methods

- Randomised controlled trials
- Cluster-randomised experiments
- Factorial experiments
- Instrumented randomisation
- Randomisation inference
- Encouragement designs

## 15.3 Observational causal methods

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
- G-computation
- Marginal structural models
- Principal stratification
- Transportability and generalisability methods

## 15.4 Causal design and diagnostics

- Confounder identification
- Collider assessment
- Positivity assessment
- Covariate balance diagnostics
- Instrument validity assessment
- Parallel-trends assessment
- Negative controls
- Sensitivity analysis
- E-value analysis
- Mediation identification assumptions

---

# 16. STOCHASTIC PROCESSES

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
- Point processes
- Marked point processes
- Spatial stochastic processes

---

# 17. RELIABILITY AND QUALITY STATISTICS

## 17.1 Reliability analysis

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
- Stress-strength models
- Degradation modelling
- Warranty analysis

## 17.2 Statistical quality control

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
- Multivariate control charts
- Process capability analysis
- Process performance analysis
- Acceptance sampling
- Six Sigma statistical methods
- Measurement-system analysis

---

# 18. EPIDEMIOLOGICAL AND BIOSTATISTICAL METHODS

## 18.1 Disease frequency

- Incidence
- Incidence rate
- Cumulative incidence
- Prevalence
- Point prevalence
- Period prevalence
- Mortality rate
- Case-fatality proportion
- Standardised mortality ratios
- Age-specific rates
- Person-time rates

## 18.2 Measures of association and impact

- Risk ratio
- Rate ratio
- Odds ratio
- Prevalence ratio
- Risk difference
- Attributable risk
- Population attributable fraction
- Number needed to treat
- Number needed to harm
- Standardised rate ratios

## 18.3 Epidemiological analysis

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
- Screening programme evaluation
- Infectious-disease modelling
- Transmission modelling
- Reproductive number estimation
- Meta-analysis of epidemiological studies

## 18.4 Clinical and biomedical statistics

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
- Clustered clinical data analysis
- Diagnostic and screening evaluation
- Biomarker analysis
- Competing-risk analysis

---

# 19. PSYCHOMETRICS AND MEASUREMENT THEORY

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
- Content validity
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
- Latent variable modelling
- Multidimensional item response theory
- Computerised adaptive testing

---

# 20. STATISTICAL LEARNING AND PREDICTIVE MODELLING

## 20.1 Supervised learning

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
- Neural networks

## 20.2 Unsupervised learning

- Clustering
- Dimension reduction
- Principal component analysis
- Factor analysis
- Anomaly detection
- Association-rule mining
- Density estimation
- Latent class models

## 20.3 Model evaluation

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
- External validation
- Temporal validation
- Model drift assessment
- Decision-curve analysis

## 20.4 Advanced learning methods

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
- Explainable machine learning
- Fairness assessment
- Model calibration
- Distribution shift assessment

---

# PART VII — ADDITIONAL AND ADVANCED STATISTICAL DOMAINS

# 21. MATHEMATICAL STATISTICS AND STATISTICAL THEORY

This domain contains the mathematical theory underlying statistical procedures.

- Statistical decision theory
- Statistical likelihood theory
- Sufficiency
- Completeness
- Exponential families
- Rao–Blackwell theorem
- Lehmann–Scheffé theorem
- Cramér–Rao lower bound
- Neyman–Pearson lemma
- Uniformly most powerful tests
- Likelihood-ratio testing
- Asymptotic theory
- Large-sample theory
- Empirical process theory
- U-statistics
- M-estimation
- Z-estimation
- Robust statistical theory
- Minimax estimation
- Admissibility
- Information-theoretic approaches to statistics

# 22. LONGITUDINAL AND PANEL DATA ANALYSIS

- Repeated-measures analysis
- Longitudinal mixed-effects models
- Generalised estimating equations
- Growth-curve models
- Latent growth models
- Random-intercept models
- Random-slope models
- Panel-data regression
- Fixed-effects models
- Random-effects models
- Dynamic panel models
- Difference and system GMM
- Cross-lagged panel models
- Longitudinal mediation models
- Missingness in longitudinal data
- Joint longitudinal-survival models

# 23. EXTREME-VALUE STATISTICS

- Extreme-value theory
- Generalised extreme-value distribution
- Generalised Pareto distribution
- Block maxima methods
- Peaks-over-threshold methods
- Return-level estimation
- Tail-index estimation
- Extreme quantile estimation
- Multivariate extreme-value models
- Tail dependence
- Extreme-value regression

# 24. COMPOSITIONAL DATA ANALYSIS

- Compositional data fundamentals
- Simplex geometry
- Closure operation
- Additive log-ratio transformation
- Centred log-ratio transformation
- Isometric log-ratio transformation
- Compositional descriptive analysis
- Compositional regression
- Compositional principal component analysis
- Compositional clustering
- Zero replacement methods
- Subcomposition analysis

# 25. FUNCTIONAL DATA ANALYSIS

- Functional data representation
- Functional descriptive statistics
- Functional principal component analysis
- Functional regression
- Functional linear models
- Functional ANOVA
- Functional clustering
- Functional classification
- Functional time-series analysis
- Smoothing and basis expansion
- Functional mixed models

# 26. DIRECTIONAL AND CIRCULAR STATISTICS

- Circular data description
- Mean direction
- Circular variance
- Circular concentration
- von Mises distribution
- Wrapped distributions
- Circular correlation
- Tests for circular uniformity
- Directional regression
- Spherical statistics
- Orientation data analysis

# 27. NETWORK AND GRAPH STATISTICS

- Network descriptive statistics
- Degree distributions
- Centrality measures
- Network density
- Community detection
- Exponential random graph models
- Stochastic block models
- Network regression
- Link prediction
- Network dependence models
- Temporal network analysis
- Spatial network analysis

# 28. COMBINATORIAL AND INFORMATION-THEORETIC METHODS

- Entropy
- Conditional entropy
- Mutual information
- Kullback–Leibler divergence
- Jensen–Shannon divergence
- Information criteria
- Minimum description length
- Permutation entropy
- Information-theoretic feature selection
- Statistical complexity measures

# 29. ECONOMETRIC AND FINANCIAL STATISTICS

- Ordinary least squares econometrics
- Instrumental-variable econometrics
- Simultaneous equation models
- Two-stage least squares
- Three-stage least squares
- Generalised method of moments
- Panel-data econometrics
- Time-series econometrics
- Cointegration
- Vector error-correction models
- ARCH and GARCH models
- Stochastic volatility models
- Event studies
- Financial risk modelling
- Value-at-risk
- Expected shortfall
- Portfolio risk estimation
- Duration models
- Limited dependent-variable models

---

# PART VIII — CROSS-CUTTING STATISTICAL CAPABILITIES

# 30. EFFECT-SIZE AND ASSOCIATION MEASURES

Effect sizes and measures of association are reporting quantities, not necessarily standalone analysis methods.

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
- Intraclass correlation
- Concordance measures

The catalogue must distinguish standardised effect sizes from model parameters and measures of association. For example, an odds ratio is a measure of association, while Cohen's d is a standardised mean-difference effect size.

# 31. ASSUMPTION TESTING AND STATISTICAL DIAGNOSTICS

Diagnostics are supporting procedures used to evaluate data, models and analytical assumptions. They are not automatically primary analysis methods.

## 31.1 Distributional diagnostics

- Shapiro–Wilk test
- Anderson–Darling test
- Kolmogorov–Smirnov test
- Lilliefors test
- Jarque–Bera test
- Q–Q plot assessment
- P–P plot assessment
- Skewness and kurtosis assessment

## 31.2 Variance and dependence diagnostics

- Levene's test
- Brown–Forsythe test
- Bartlett's test
- Fligner–Killeen test
- Durbin–Watson test
- Breusch–Pagan test
- White's test
- Breusch–Godfrey test
- Intraclass correlation assessment
- Dependence assessment

## 31.3 Regression diagnostics

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
- Calibration diagnostics
- Link-function diagnostics

## 31.4 General data diagnostics

- Missing-data analysis
- Missingness-pattern analysis
- Missing completely at random assessment
- Missing at random assessment
- Missing not at random sensitivity assessment
- Outlier detection
- Duplicate detection
- Data consistency checks
- Data validity checks
- Distributional anomaly detection
- Range and logical validation
- Data integrity checks

**Important:** MCAR, MAR and MNAR are missing-data mechanisms. They cannot generally be conclusively classified from observed data alone. Diagnostics may provide evidence, but assumptions and sensitivity analyses remain necessary.

# 32. RESAMPLING, SIMULATION AND COMPUTATIONAL INFERENCE

These are computational procedures that support many statistical methods and inference paradigms.

- Bootstrap
- Parametric bootstrap
- Non-parametric bootstrap
- Cluster bootstrap
- Block bootstrap
- Wild bootstrap
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
- Parametric simulation
- Posterior simulation
- Variance reduction methods

# 33. META-ANALYSIS AND EVIDENCE SYNTHESIS

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
- Prediction intervals in meta-analysis
- Small-study effects assessment
- Robust variance estimation

# 34. MISSING-DATA STATISTICS

## 34.1 Missingness concepts

- Missing completely at random
- Missing at random
- Missing not at random
- Monotone missingness
- Arbitrary missingness patterns
- Missingness indicators
- Missingness mechanisms

## 34.2 Missing-data methods

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
- Expectation-maximisation methods
- Pattern-mixture models
- Selection models
- Delta-adjustment sensitivity analysis
- Sensitivity analysis for missing-not-at-random mechanisms

# 35. STATISTICAL REPORTING

Every applicable analysis should support structured reporting of:

- Research objective
- Research question
- Statistical purpose
- Knowledge area
- Selected method and model
- Method-selection rationale
- Variable roles and measurement scales
- Study design
- Sampling design
- Target population
- Estimand, where applicable
- Hypotheses, where applicable
- Sample size and analytical sample
- Missing-data handling
- Test statistic or model estimates
- Degrees of freedom, where applicable
- P-value, where applicable
- Confidence interval or credible interval, where applicable
- Effect size or association measure, where applicable
- Assumption checks
- Model diagnostics
- Sensitivity analyses
- Limitations
- Interpretation
- Reproducibility information
- Software and method version information

# 36. VISUALISATION AND PRESENTATION

TimanStat should support appropriate visualisations, including:

- Descriptive charts
- Frequency charts
- Distribution plots
- Box plots
- Violin plots
- Scatter plots
- Correlation plots
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
- Spatial cluster maps
- Time-series plots
- Forecast plots
- Control charts
- Meta-analysis funnel plots
- Effect-size plots
- Network graphs
- Functional data plots
- Circular plots

A visualisation is a presentation entity. It must not be registered as a statistical test or model merely because it is associated with one.

---

# PART IX — MACHINE-READABLE KNOWLEDGE ARCHITECTURE

# 37. STATISTICAL TAXONOMY

Every catalogue entry must be classified using independent dimensions.

## 37.1 Statistical purpose

Permitted values:

- `descriptive`
- `inferential`
- `predictive`
- `causal`
- `exploratory`
- `decision_support`
- `foundational`
- `multiple`

A procedure may have more than one applicable purpose.

## 37.2 Knowledge area

Examples:

- `descriptive_statistics`
- `probability_theory`
- `frequentist_inference`
- `bayesian_statistics`
- `regression`
- `experimental_design`
- `survey_statistics`
- `multivariate_statistics`
- `nonparametric_statistics`
- `time_series`
- `survival_analysis`
- `spatial_statistics`
- `causal_inference`
- `stochastic_processes`
- `reliability_statistics`
- `epidemiology`
- `psychometrics`
- `statistical_learning`
- `mathematical_statistics`
- `longitudinal_analysis`
- `extreme_value_statistics`
- `compositional_data_analysis`
- `functional_data_analysis`
- `directional_statistics`
- `network_statistics`
- `econometrics`

## 37.3 Entity type

Each catalogue record must have one primary entity type:

- `method` — a statistical procedure used to answer an analytical question.
- `model` — a mathematical or probabilistic representation of a data-generating process or relationship.
- `design` — a structure governing how observations, treatments or samples are generated.
- `diagnostic` — a procedure used to assess data, assumptions or model adequacy.
- `algorithm` — a computational procedure used to estimate, optimise or simulate.
- `measure` — a statistic, parameter, effect size or summary quantity.
- `visualization` — a graphical representation of data, estimates or model behaviour.
- `theory` — a foundational statistical principle or mathematical result.
- `distribution` — a probability distribution used in statistical modelling.

An entity may have related records of other types, but it must not be ambiguously registered as all types at once.

## 37.4 Method family

Examples:

- `central_tendency`
- `dispersion`
- `distribution_shape`
- `association`
- `mean_comparison`
- `categorical_testing`
- `goodness_of_fit`
- `regression`
- `classification`
- `clustering`
- `dimension_reduction`
- `survival`
- `forecasting`
- `causal_estimation`
- `sampling_estimation`
- `variance_estimation`
- `resampling`
- `measurement`
- `reliability`

## 37.5 Inference paradigm

Applicable values:

- `frequentist`
- `bayesian`
- `randomization_based`
- `likelihood_based`
- `design_based`
- `model_based`
- `distribution_free`
- `not_applicable`
- `multiple`

The paradigm must not be confused with the knowledge area. For example, Bayesian regression belongs to the regression knowledge area and uses the Bayesian inference paradigm.

## 37.6 Application domain

Examples:

- `general_research`
- `biostatistics`
- `epidemiology`
- `public_health`
- `agriculture`
- `economics`
- `education`
- `business`
- `psychology`
- `engineering`
- `environmental_science`
- `social_science`

Application domains are cross-cutting tags. They should not determine the mathematical identity of a method.

---

# 38. CANONICAL IDENTIFIERS AND RELATIONSHIPS

Every statistical entity must have one canonical record and a unique identifier.

Recommended identifier conventions:

- `desc.mean.arithmetic`
- `desc.shape.skewness`
- `infer.t_test.independent.welch`
- `infer.anova.one_way`
- `model.regression.linear.multiple`
- `model.regression.logistic.binary`
- `design.experiment.randomized_complete_block`
- `diagnostic.normality.shapiro_wilk`
- `algorithm.resampling.bootstrap.nonparametric`
- `measure.effect.cohens_d`
- `viz.distribution.histogram`
- `theory.probability.central_limit_theorem`

Identifiers are illustrative conventions and may be refined before registry implementation.

## 38.1 Relationship types

The registry should support explicit relationships such as:

- `belongs_to`
- `is_a`
- `uses_algorithm`
- `requires_design`
- `analysed_by`
- `has_diagnostic`
- `reports_measure`
- `has_visualization`
- `alternative_to`
- `extends`
- `related_to`
- `requires_assumption`
- `estimates`
- `implemented_by`

Examples:

- One-way ANOVA `belongs_to` mean-comparison methods.
- One-way ANOVA `reports_measure` eta-squared or omega-squared.
- Randomised complete block design `analysed_by` a suitable blocked model.
- Shapiro–Wilk `is_a` diagnostic.
- Bootstrap `is_a` computational algorithm.
- Cohen's d `is_a` effect-size measure.

## 38.2 No duplicate definitions

If a method appears in several knowledge areas, it must have one canonical record and multiple relationships or tags.

For example:

- Spearman correlation may be relevant to descriptive association, non-parametric statistics and inferential analysis.
- Bootstrap may support confidence intervals, model validation and computational inference.
- ANOVA may be relevant to classical inference, experimental design and multivariate analysis.

These cross-references must not create duplicate method identities.

---

# 39. STATISTICAL METHOD METADATA SCHEMA

Every executable or selectable statistical method should have a structured record.

## 39.1 Identity and classification

- `entity_id`
- `name`
- `aliases`
- `entity_type`
- `parent_id`
- `related_entity_ids`
- `knowledge_area`
- `method_family`
- `statistical_purpose`
- `inference_paradigm`
- `application_domains`
- `tags`

## 39.2 Method description

- `description`
- `statistical_objective`
- `research_questions`
- `appropriate_use_cases`
- `inappropriate_use_cases`
- `methodological_rationale`
- `limitations`

## 39.3 Research and data requirements

- `outcome_requirements`
- `predictor_requirements`
- `variable_roles`
- `measurement_scales`
- `data_structure_requirements`
- `sample_size_requirements`
- `study_design_requirements`
- `sampling_design_requirements`
- `independence_structure`
- `grouping_requirements`
- `time_structure_requirements`
- `missing_data_requirements`

## 39.4 Statistical specification

- `estimand`
- `hypotheses`
- `model_structure`
- `link_function`
- `probability_distribution`
- `estimation_method`
- `inference_method`
- `assumptions`
- `identification_assumptions`
- `selection_rules`

## 39.5 Outputs and interpretation

- `test_statistics`
- `parameter_estimates`
- `effect_sizes`
- `association_measures`
- `interval_estimates`
- `uncertainty_measures`
- `model_fit_statistics`
- `diagnostics`
- `interpretation_guidance`
- `reporting_requirements`
- `visualization_options`

## 39.6 Computation and implementation

- `algorithm_requirements`
- `computational_requirements`
- `supported_engines`
- `implementation_status`
- `verification_status`
- `validation_scope`
- `known_limitations`
- `references`
- `version`

Fields may be optional where they do not apply. A descriptive frequency table, for example, does not require a hypothesis or estimand.

---

# 40. IMPLEMENTATION AND VERIFICATION STATUS

Implementation status and verification status must be separate.

## 40.1 Implementation status

Permitted values:

- `catalogued` — recognised in the statistical knowledge catalogue.
- `planned` — selected for future implementation.
- `in_development` — implementation work has begun.
- `implemented` — executable functionality exists.
- `deprecated` — no longer recommended for new use.

## 40.2 Verification status

Permitted values:

- `not_tested`
- `unit_tested`
- `integration_tested`
- `numerically_verified`
- `methodologically_reviewed`
- `validated`

These statuses describe different levels of evidence. A method should not be marked `validated` merely because its code runs or its unit tests pass.

## 40.3 Validation requirements

Validation should consider:

- Correctness of the statistical formula
- Correct handling of missing values
- Correct handling of edge cases
- Numerical stability
- Agreement with trusted reference implementations
- Agreement with known analytical examples
- Assumption and diagnostic behaviour
- Reproducibility
- Appropriate interpretation
- Documented limitations

---

# PART X — TIMANSTAT ANALYTICAL ARCHITECTURE

# 41. STATISTICAL ANALYSIS WORKFLOW

TimanStat should use a structured analytical workflow:

1. **Objective understanding:** interpret the research question and intended decision.
2. **Data inspection:** identify variables, measurement scales, data structure and quality.
3. **Statistical classification:** identify the purpose, knowledge area and relevant method families.
4. **Estimand identification:** establish the quantity or relationship the user wants to describe, estimate, test or predict.
5. **Method recommendation:** identify suitable methods and explain alternatives.
6. **Clarification and approval:** ask the user for missing information or confirmation where necessary.
7. **Model specification:** define variables, outcomes, predictors, factors, covariates, interactions, design and hypotheses.
8. **Specification validation:** check data compatibility, assumptions and study-design constraints.
9. **Execution:** call the appropriate validated statistical engine.
10. **Result verification:** check numerical outputs, diagnostics and consistency.
11. **Interpretation:** explain estimates, uncertainty, effect sizes and limitations.
12. **Communication:** produce tables, visualisations and reports.

Not every analysis requires every stage. A descriptive summary, for example, does not require a hypothesis test or inferential model.

# 42. SEPARATION OF RESPONSIBILITIES

TimanStat should separate the following architectural responsibilities:

## 42.1 Knowledge catalogue

Stores statistical concepts, methods, models, designs, diagnostics, algorithms, measures and their relationships.

## 42.2 Objective and domain classifier

Interprets the research question and identifies relevant statistical purposes and knowledge areas.

## 42.3 Method selector

Evaluates candidate methods using research objectives, variable roles, measurement scales, study design, sampling design, data structure and assumptions.

## 42.4 Statistical model specification

Converts the selected method into a structured, machine-readable model specification.

## 42.5 Validation and diagnostics engine

Checks the proposed specification, data compatibility, assumptions and diagnostic requirements.

## 42.6 Statistical computation engine

Executes validated statistical procedures using controlled, tested functions. It must not execute arbitrary code generated from a user prompt.

## 42.7 Result verification layer

Checks computational outputs, numerical properties, expected ranges and relevant reference cases.

## 42.8 Interpretation and reporting layer

Converts verified statistical outputs into explanations, tables, visualisations and reproducible reports.

---

# 43. STATISTICAL MODEL SPECIFICATION

A model specification should be separate from the analysis request and the computed result.

A general model specification may contain:

- `analysis_type`
- `outcome_variable`
- `predictor_variables`
- `factors`
- `covariates`
- `interaction_terms`
- `grouping_variables`
- `time_variable`
- `cluster_variable`
- `study_design`
- `sampling_design`
- `estimand`
- `hypotheses`
- `assumptions`
- `estimation_settings`
- `inference_settings`
- `missing_data_strategy`
- `diagnostic_plan`
- `execution_settings`

The specification must use controlled identifiers and validated variable references. It must not accept arbitrary executable instructions.

---

# 44. ARCHITECTURAL PRINCIPLES

1. The catalogue must be comprehensive, structured and extensible.
2. Every entity must have a unique canonical identifier.
3. Statistical purposes, knowledge areas, method families and entity types must remain distinct.
4. Each entity must have one primary entity type.
5. Related methods must be connected through explicit relationships.
6. Methods must not be duplicated merely because they are relevant to multiple domains.
7. Descriptive and inferential analysis must remain clearly distinguished.
8. Bayesian and frequentist approaches must be represented as inference paradigms, not as mutually exclusive statistical universes.
9. Experimental designs must be distinguished from statistical analysis methods.
10. Diagnostics must be distinguished from primary analysis methods.
11. Computational algorithms must be distinguished from statistical models.
12. Effect sizes and other measures must be distinguished from methods.
13. Visualisations must be distinguished from statistical procedures.
14. Selection must consider the research objective, estimand, data structure, variable types, sampling design, study design and assumptions.
15. Method selection must explain why a method is suitable and identify important alternatives.
16. Statistical calculations must be separated from method selection, validation and reporting.
17. No method should be represented as operational merely because it is registered.
18. Verification and methodological validation must be documented.
19. The framework must support both classical and emerging statistical disciplines.
20. New methods must be incorporable without redesigning the core architecture.

# 45. FUTURE EXTENSIBILITY

The taxonomy should accommodate additional statistical fields and methods, including:

- Advanced causal machine learning
- Advanced statistical decision theory
- Spatial-temporal modelling
- Advanced functional data analysis
- Advanced compositional data analysis
- High-dimensional statistics
- Statistical genetics
- Genomics and omics statistics
- Network science
- Statistical methods for artificial intelligence
- Privacy-preserving statistics
- Differential privacy
- Federated statistical analysis
- Distribution-free and robust machine learning
- Advanced Bayesian computation
- Statistical methods for complex adaptive systems

These areas may be expanded as the knowledge catalogue matures.

---

**END OF TIMANSTAT STATISTICAL METHODS CATALOGUE — VERSION 2.1**

**Version note:** Version 2.1 preserves the comprehensive scope of Version 2.0 while introducing a multidimensional taxonomy, canonical entity records, explicit relationships, an expanded metadata schema and a clearer separation between statistical knowledge, method selection, model specification, diagnostics, computation, verification and reporting.
