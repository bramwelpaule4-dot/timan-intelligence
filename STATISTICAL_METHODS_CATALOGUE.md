# TIMANSTAT STATISTICAL METHODS CATALOGUE

**Version:** 2.1  
**Status:** Proposed comprehensive statistical knowledge and methodology blueprint  
**Product:** TimanStat  
**Organisation:** Timan Analytics  
**Supersedes:** Version 2.0

---

# 1. PURPOSE AND SCOPE

## 1.1 Purpose

This catalogue defines the statistical knowledge, methods, models, research designs, diagnostics, computational procedures and reporting capabilities that TimanStat should recognise and eventually support.

TimanStat is intended to operate as an intelligent statistical analysis platform. It should not merely execute isolated statistical tests. It should understand research objectives, identify the appropriate analytical approach, examine data suitability, formulate statistical models, validate analytical specifications, execute appropriate computations and communicate results responsibly.

The catalogue therefore establishes the methodological knowledge base from which TimanStat's analysis-selection and statistical-execution capabilities will be developed.

## 1.2 Application scope

The catalogue is intended to support quantitative analysis across:

- General research and applied statistics.
- Mathematics and mathematical statistics.
- Biostatistics and biomedical research.
- Epidemiology and public health.
- Clinical research and clinical trials.
- Agriculture and agricultural research.
- Economics and econometrics.
- Education and educational assessment.
- Business and management.
- Social sciences and behavioural research.
- Environmental and ecological research.
- Engineering and industrial research.
- Demography and population studies.
- Survey research and development programmes.
- Data science and statistical learning.

## 1.3 Scope of statistical capabilities

TimanStat should progressively recognise and support:

1. Descriptive statistics and exploratory data analysis.
2. Probability theory and probability distributions.
3. Mathematical statistics and statistical inference.
4. Frequentist and Bayesian inference.
5. Regression and generalised linear models.
6. Experimental design and design of experiments.
7. Sampling and survey statistics.
8. Multivariate statistics.
9. Non-parametric and distribution-free statistics.
10. Time-series analysis and forecasting.
11. Survival and event-history analysis.
12. Spatial and spatiotemporal statistics.
13. Causal inference.
14. Stochastic processes.
15. Reliability and quality statistics.
16. Epidemiological and biostatistical methods.
17. Psychometrics and measurement theory.
18. Longitudinal and repeated-measures analysis.
19. Statistical learning and predictive modelling.
20. Functional and compositional data analysis.
21. Extreme-value and directional statistics.
22. Network statistics.
23. Missing-data statistics.
24. Meta-analysis and evidence synthesis.
25. Statistical computing, simulation and numerical methods.
26. Statistical reporting and visualisation.

## 1.4 Catalogue inclusion versus implementation

This catalogue describes the intended methodological scope of TimanStat.

It does not imply that every listed method is currently implemented, tested, validated or available to users.

The catalogue must distinguish:

- What TimanStat knows about.
- What TimanStat can recommend.
- What TimanStat can specify as an analytical model.
- What TimanStat can execute.
- What TimanStat can validate.
- What TimanStat can interpret and report.

A method may be recognised and recommended while its computational implementation remains unavailable.

---

# PART I: CLASSIFICATION AND STATISTICAL KNOWLEDGE ARCHITECTURE

# 2. STATISTICAL CLASSIFICATION FRAMEWORK

## 2.1 Analytical purpose

Every analytical procedure should be classified according to its primary purpose. The purposes are not necessarily mutually exclusive.

### 2.1.1 Descriptive analysis

Organises, summarises and presents observed data.

Examples:

- Frequencies and percentages.
- Measures of central tendency.
- Measures of dispersion.
- Skewness and kurtosis.
- Cross-tabulations.
- Descriptive correlation.
- Graphical summaries.

### 2.1.2 Exploratory analysis

Investigates patterns, relationships, unusual observations and potential structures in data without necessarily beginning with a formal confirmatory hypothesis.

Examples:

- Exploratory data analysis.
- Distribution exploration.
- Outlier identification.
- Correlation exploration.
- Principal component exploration.
- Cluster exploration.

### 2.1.3 Inferential analysis

Uses sample information, probability models or other justified inferential frameworks to make statements about a population or an underlying data-generating process.

Examples:

- Estimation.
- Confidence intervals.
- Hypothesis testing.
- Regression inference.
- Bayesian posterior inference.
- Randomisation inference.

### 2.1.4 Predictive analysis

Develops and evaluates models intended to predict unknown or future outcomes.

Examples:

- Regression prediction.
- Classification.
- Time-series forecasting.
- Survival prediction.
- Machine learning.

### 2.1.5 Causal analysis

Estimates causal effects or evaluates what would happen under specified interventions, subject to identification assumptions.

Examples:

- Randomised experiments.
- Difference-in-differences.
- Instrumental-variable estimation.
- Regression discontinuity.
- Propensity-score methods.

### 2.1.6 Decision and optimisation analysis

Uses statistical information to support decisions under uncertainty.

Examples:

- Bayesian decision theory.
- Decision analysis.
- Optimal experimental design.
- Statistical decision rules.
- Expected-loss analysis.

## 2.2 Statistical knowledge areas

Knowledge areas organise related statistical concepts and procedures.

The primary knowledge areas include:

- Descriptive statistics.
- Probability theory.
- Mathematical statistics.
- Frequentist inference.
- Bayesian statistics.
- Regression and generalised linear modelling.
- Experimental design.
- Sampling and survey statistics.
- Multivariate statistics.
- Non-parametric statistics.
- Time-series analysis.
- Survival analysis.
- Spatial statistics.
- Causal inference.
- Stochastic processes.
- Reliability and quality statistics.
- Epidemiology and biostatistics.
- Psychometrics.
- Longitudinal data analysis.
- Statistical learning.
- Computational statistics.
- Meta-analysis.
- Missing-data statistics.

A method may belong to more than one knowledge area through explicit relationships and tags.

## 2.3 Method families

Method families group procedures according to their statistical function.

Examples include:

- Frequency estimation.
- Distribution summarisation.
- Location estimation.
- Dispersion estimation.
- Difference testing.
- Association analysis.
- Goodness-of-fit testing.
- Regression modelling.
- Classification.
- Clustering.
- Dimension reduction.
- Survival modelling.
- Forecasting.
- Causal effect estimation.
- Variance estimation.
- Resampling inference.

## 2.4 Statistical inference paradigms

The inference paradigm identifies the framework used to reason about uncertainty.

### 2.4.1 Frequentist inference

Uses repeated-sampling properties and sampling distributions.

### 2.4.2 Bayesian inference

Combines prior information and likelihood information to obtain posterior distributions.

### 2.4.3 Randomisation-based inference

Uses a randomisation mechanism or permutation distribution to evaluate hypotheses or treatment effects.

### 2.4.4 Likelihood-based inference

Uses likelihood functions and likelihood-based procedures for estimation, comparison and uncertainty assessment.

These paradigms should not be treated as mutually exclusive knowledge areas. A statistical model or analytical question may support more than one inferential approach.

## 2.5 Statistical entity types

Every catalogue record must have an explicit entity type.

### 2.5.1 Method

A defined analytical procedure.

Examples: Welch's t-test, Mann–Whitney U test, Kaplan–Meier estimation.

### 2.5.2 Model

A mathematical or probabilistic representation of a data-generating process or relationship.

Examples: linear regression model, logistic regression model, Cox proportional hazards model.

### 2.5.3 Study design

A structure governing how observations, treatments, exposures or measurements are organised and obtained.

Examples: randomised complete block design, cohort study, crossover trial.

### 2.5.4 Diagnostic

A procedure or measure used to assess data, assumptions, model fit or analytical reliability.

Examples: Shapiro–Wilk test, variance inflation factor, Cook's distance.

### 2.5.5 Computational algorithm

A numerical or simulation-based procedure used to estimate, approximate or execute statistical computations.

Examples: Gibbs sampling, Hamiltonian Monte Carlo, bootstrap resampling.

### 2.5.6 Statistical measure

A quantity used to describe data, association, uncertainty or effect magnitude.

Examples: standard deviation, odds ratio, Cohen's d, hazard ratio.

### 2.5.7 Visualisation

A graphical representation of data, estimates, model behaviour or uncertainty.

Examples: histogram, Q–Q plot, forest plot, Kaplan–Meier curve.

### 2.5.8 Statistical principle or theory

A foundational concept governing statistical reasoning.

Examples: Central Limit Theorem, randomisation, sufficiency, likelihood theory.

### 2.5.9 Reporting procedure

A procedure for presenting, interpreting or communicating statistical findings.

Examples: structured hypothesis-test reporting, model-performance reporting.

## 2.6 Canonical classification principle

Each entity must have one canonical record and one unique identifier.

The same method must not be independently registered in multiple catalogue sections.

Where a method applies to multiple domains or purposes, the catalogue should use:

- One canonical record.
- Multiple classification tags.
- Parent-child relationships where appropriate.
- Cross-references to related methods and models.

For example, Spearman correlation may be relevant to descriptive association, non-parametric statistics and inferential association analysis. It should have one canonical method record, not three independent definitions.

---

# PART II: FOUNDATIONAL STATISTICS

# 3. DESCRIPTIVE STATISTICS

Descriptive statistics organise, summarise and present observed data.

## 3.1 Frequency and distribution analysis

- Frequency distribution.
- Absolute frequency.
- Relative frequency.
- Cumulative frequency.
- Cumulative relative frequency.
- Proportions.
- Percentages.
- Grouped frequency distribution.
- Frequency density.
- Cross-tabulation.
- Contingency tables.
- Joint frequency distributions.
- Marginal frequency distributions.
- Conditional frequency distributions.
- Two-way frequency tables.
- Multi-way frequency tables.
- Weighted frequency distributions.

## 3.2 Measures of central tendency

- Arithmetic mean.
- Weighted arithmetic mean.
- Geometric mean.
- Harmonic mean.
- Median.
- Mode.
- Trimmed mean.
- Winsorised mean.
- Midrange.
- Trimean.
- Geometric median.
- Robust location estimators.

## 3.3 Measures of dispersion

- Minimum and maximum.
- Range.
- Interquartile range.
- Quartile deviation.
- Mean absolute deviation.
- Median absolute deviation.
- Population variance.
- Sample variance.
- Population standard deviation.
- Sample standard deviation.
- Coefficient of variation.
- Relative dispersion measures.
- Average absolute deviation.
- Interdecile range.
- Robust scale estimators.

## 3.4 Measures of position

- Quartiles.
- Deciles.
- Percentiles.
- Quantiles.
- Quintiles.
- Z-scores.
- Standard scores.
- Percentile ranks.
- Rank statistics.
- Standardised values.
- Studentised values.

## 3.5 Measures of distribution shape

- Skewness.
- Positive skewness.
- Negative skewness.
- Symmetry assessment.
- Kurtosis.
- Excess kurtosis.
- Mesokurtic distribution.
- Leptokurtic distribution.
- Platykurtic distribution.
- Higher-order moments.
- L-moments.
- Robust measures of skewness.
- Robust measures of kurtosis.

## 3.6 Descriptive association and relationship measures

- Covariance.
- Pearson correlation coefficient.
- Spearman rank correlation coefficient.
- Kendall's tau.
- Phi coefficient.
- Cramér's V.
- Contingency coefficient.
- Point-biserial correlation coefficient.
- Rank-biserial correlation coefficient.
- Polychoric correlation.
- Tetrachoric correlation.
- Polyserial correlation.
- Distance correlation.
- Mutual information.
- Intraclass correlation coefficient.

The descriptive association coefficient must be distinguished from a corresponding inferential significance test or interval estimate.

## 3.7 Graphical descriptive methods

### Categorical data

- Bar chart.
- Grouped bar chart.
- Stacked bar chart.
- Pie chart.
- Mosaic plot.
- Pareto chart.
- Population pyramid.

### Numerical data

- Histogram.
- Frequency polygon.
- Ogive.
- Box plot.
- Violin plot.
- Dot plot.
- Stem-and-leaf plot.
- Density plot.
- Empirical cumulative distribution plot.
- Strip plot.
- Beeswarm plot.

### Relationship visualisations

- Scatter plot.
- Bubble plot.
- Line graph.
- Heatmap.
- Pair plot.
- Correlogram.
- Parallel-coordinate plot.
- Radar chart.

### Distribution diagnostics and comparisons

- Q–Q plot.
- P–P plot.
- Error-bar plot.
- Ridgeline plot.

## 3.8 Exploratory data analysis

- Univariate analysis.
- Bivariate analysis.
- Multivariate exploratory analysis.
- Distribution exploration.
- Outlier identification.
- Missing-data exploration.
- Duplicate-record analysis.
- Grouped descriptive analysis.
- Stratified descriptive analysis.
- Robust exploratory summaries.
- Relationship exploration.
- Pattern detection.
- Data transformation exploration.
- Exploratory dimension reduction.

---

# 4. PROBABILITY THEORY AND DISTRIBUTIONS

Probability theory provides the mathematical foundation for statistical modelling and inference.

## 4.1 Probability fundamentals

- Classical probability.
- Empirical probability.
- Axiomatic probability.
- Conditional probability.
- Joint probability.
- Marginal probability.
- Independence of events.
- Mutually exclusive events.
- Bayes' theorem.
- Law of total probability.
- Combinatorics.
- Permutations and combinations.
- Conditional independence.
- Probability spaces.
- Events and sigma-algebras.
- Probability measures.

## 4.2 Random variables

- Discrete random variables.
- Continuous random variables.
- Mixed random variables.
- Probability mass functions.
- Probability density functions.
- Cumulative distribution functions.
- Joint distributions.
- Marginal distributions.
- Conditional distributions.
- Transformations of random variables.
- Order statistics.
- Random vectors.

## 4.3 Probability moments and properties

- Mathematical expectation.
- Variance.
- Standard deviation.
- Covariance.
- Correlation.
- Conditional expectation.
- Moment-generating functions.
- Characteristic functions.
- Probability-generating functions.
- Higher-order moments.
- Conditional variance.
- Jensen's inequality.
- Markov's inequality.
- Chebyshev's inequality.

## 4.4 Discrete probability distributions

- Bernoulli distribution.
- Binomial distribution.
- Geometric distribution.
- Negative binomial distribution.
- Hypergeometric distribution.
- Poisson distribution.
- Discrete uniform distribution.
- Multinomial distribution.
- Beta-binomial distribution.
- Discrete Laplace distribution.
- Zipf distribution.
- Zero-truncated distributions.

## 4.5 Continuous probability distributions

- Uniform distribution.
- Normal distribution.
- Standard normal distribution.
- Exponential distribution.
- Gamma distribution.
- Beta distribution.
- Chi-square distribution.
- Student's t-distribution.
- F-distribution.
- Weibull distribution.
- Log-normal distribution.
- Logistic distribution.
- Cauchy distribution.
- Pareto distribution.
- Laplace distribution.
- Rayleigh distribution.
- Gumbel distribution.
- Inverse Gaussian distribution.
- Generalised extreme-value distribution.
- Generalised Pareto distribution.
- Student's t multivariate distribution.
- Dirichlet distribution.
- Multivariate normal distribution.
- Multivariate t-distribution.

## 4.6 Sampling distributions and limit theorems

- Sampling distributions.
- Central Limit Theorem.
- Law of Large Numbers.
- Distribution of sample means.
- Distribution of sample proportions.
- Distribution of sample variance.
- Standard error distributions.
- Order-statistic distributions.
- Asymptotic distributions.
- Delta method.
- Slutsky's theorem.
- Continuous mapping theorem.
- Weak convergence.
- Almost-sure convergence.
- Convergence in probability.
- Convergence in distribution.

---

# PART III: MATHEMATICAL STATISTICS AND INFERENTIAL ANALYSIS

# 5. MATHEMATICAL STATISTICS

Mathematical statistics provides the theoretical foundation for estimation, inference and statistical decision-making.

## 5.1 Statistical foundations

- Population and sample theory.
- Statistical models.
- Parametric statistical models.
- Non-parametric statistical models.
- Semiparametric statistical models.
- Likelihood functions.
- Sampling theory.
- Statistical sufficiency.
- Ancillary statistics.
- Completeness.
- Minimal sufficiency.
- Factorisation theorem.

## 5.2 Estimation theory

- Point estimation.
- Interval estimation.
- Method of moments estimation.
- Maximum likelihood estimation.
- Least squares estimation.
- Minimum variance estimation.
- Unbiased estimation.
- Consistent estimation.
- Efficient estimation.
- Minimum variance unbiased estimation.
- Generalised method of moments.
- Bayesian estimation.
- Empirical Bayes estimation.

## 5.3 Likelihood theory

- Likelihood functions.
- Log-likelihood.
- Score functions.
- Fisher information.
- Observed information.
- Expected information.
- Likelihood-ratio tests.
- Profile likelihood.
- Wald tests.
- Score tests.
- Likelihood-based confidence intervals.
- Asymptotic likelihood theory.

## 5.4 Statistical decision theory

- Decision rules.
- Loss functions.
- Risk functions.
- Bayes risk.
- Minimax decision rules.
- Admissibility.
- Complete-class principles.
- Optimal decision rules.
- Statistical utility.
- Expected loss.
- Decision-making under uncertainty.

## 5.5 Hypothesis-testing theory

- Simple and composite hypotheses.
- Null and alternative hypotheses.
- Neyman–Pearson lemma.
- Uniformly most powerful tests.
- Likelihood-ratio testing theory.
- Type I error.
- Type II error.
- Power functions.
- Most powerful tests.
- Unbiased tests.
- Multiple-testing theory.

---

# 6. CLASSICAL AND FREQUENTIST INFERENCE

## 6.1 Statistical estimation

- Point estimation.
- Interval estimation.
- Method of moments estimation.
- Maximum likelihood estimation.
- Least squares estimation.
- Minimum variance estimation.
- Unbiased estimation.
- Consistent estimation.
- Efficient estimation.
- Sufficient statistics.
- Fisher information.
- Standard errors.
- Margin of error.
- Generalised estimating equations where applicable.

## 6.2 Confidence intervals

- Confidence interval for a population mean.
- Confidence interval for a population proportion.
- Confidence interval for a variance.
- Confidence interval for a difference between means.
- Confidence interval for a difference between proportions.
- Confidence interval for correlation.
- Confidence interval for regression coefficients.
- Confidence interval for odds ratios.
- Confidence interval for risk ratios.
- Confidence interval for rate ratios.
- Confidence interval for effect sizes.
- Bootstrap confidence intervals.
- Profile likelihood confidence intervals.
- Exact confidence intervals.
- Simultaneous confidence intervals.
- Prediction intervals.
- Tolerance intervals.

## 6.3 Hypothesis testing

- Null and alternative hypotheses.
- Simple and composite hypotheses.
- One-tailed testing.
- Two-tailed testing.
- Significance levels.
- P-values.
- Critical-value methods.
- Type I error.
- Type II error.
- Statistical power.
- Minimum detectable effect.
- Multiple-testing correction.
- Family-wise error rate.
- False discovery rate.
- Bonferroni correction.
- Holm correction.
- Benjamini–Hochberg procedure.
- Benjamini–Yekutieli procedure.
- Permutation-based testing.
- Equivalence testing.
- Non-inferiority testing.
- Sequential hypothesis testing.

## 6.4 Tests of means and differences

### Parametric tests

- One-sample t-test.
- Independent-samples Student's t-test.
- Welch's independent-samples t-test.
- Paired-samples t-test.
- One-way ANOVA.
- Two-way ANOVA.
- Factorial ANOVA.
- N-way ANOVA.
- Repeated-measures ANOVA.
- Mixed-design ANOVA.
- Analysis of covariance (ANCOVA).
- Multivariate analysis of variance (MANOVA).
- Multivariate analysis of covariance (MANCOVA).
- General linear model comparisons.

### Non-parametric alternatives

- One-sample sign test.
- Two-sample sign test.
- Mann–Whitney U test.
- Wilcoxon signed-rank test.
- Kruskal–Wallis test.
- Friedman test.
- Mood's median test.
- Jonckheere–Terpstra test.
- Fligner–Policello test.
- Brunner–Munzel test.
- Aligned rank transform procedures.

## 6.5 Tests of categorical data

- Chi-square goodness-of-fit test.
- Chi-square test of independence.
- Chi-square test of homogeneity.
- Fisher's exact test.
- McNemar's test.
- Cochran's Q test.
- Binomial test.
- Multinomial test.
- One-proportion z-test.
- Two-proportion z-test.
- Exact tests for contingency tables.
- Mantel–Haenszel test.
- Cochran–Mantel–Haenszel procedures.
- Trend tests for ordered categories.
- Exact conditional inference.

## 6.6 Correlation and association inference

- Pearson correlation significance test.
- Spearman correlation significance test.
- Kendall's tau significance test.
- Partial correlation test.
- Semi-partial correlation.
- Point-biserial correlation test.
- Rank correlation tests.
- Tests for equality of correlation coefficients.
- Tests of partial correlations.
- Confidence intervals for correlation coefficients.

## 6.7 Goodness-of-fit and distribution tests

- Chi-square goodness-of-fit.
- Kolmogorov–Smirnov test.
- Shapiro–Wilk test.
- Anderson–Darling test.
- Cramér–von Mises test.
- Jarque–Bera test.
- Lilliefors test.
- D'Agostino's K-squared test.
- Levene's test.
- Brown–Forsythe test.
- Bartlett's test.
- Fligner–Killeen test.

These procedures must be classified according to what they test. Distributional tests, variance-homogeneity tests and general model diagnostics must not be treated as interchangeable.

---

# PART IV: MODELLING AND ADVANCED INFERENCE

# 7. REGRESSION AND GENERALISED LINEAR MODELS

## 7.1 Linear regression models

- Simple linear regression.
- Multiple linear regression.
- Polynomial regression.
- Interaction regression.
- Weighted least squares regression.
- Generalised least squares.
- Regression with categorical predictors.
- Regression with continuous predictors.
- Regression with dummy variables.
- Regression with transformed variables.
- Multivariate linear regression.
- Constrained linear regression.

## 7.2 Generalised linear models

- Generalised linear models.
- Binary logistic regression.
- Multinomial logistic regression.
- Ordinal logistic regression.
- Poisson regression.
- Negative binomial regression.
- Quasi-Poisson regression.
- Gamma regression.
- Inverse Gaussian regression.
- Probit regression.
- Complementary log-log regression.
- Zero-inflated Poisson regression.
- Zero-inflated negative binomial regression.
- Hurdle models.
- Beta regression.
- Tweedie regression.
- Generalised additive models for location, scale and shape.

## 7.3 Advanced regression

- Robust regression.
- Quantile regression.
- Ridge regression.
- Lasso regression.
- Elastic net regression.
- Generalised additive models.
- Non-linear regression.
- Spline regression.
- Mixed-effects regression.
- Multilevel regression.
- Hierarchical regression.
- Bayesian regression.
- Penalised regression.
- Tobit regression.
- Truncated regression.
- Censored regression.
- Sample-selection models.
- Instrumental-variable regression.
- Regression discontinuity models.
- Spatial regression.
- Panel-data regression.
- Fixed-effects models.
- Random-effects models.
- Dynamic panel models.

Hierarchical regression as a blockwise variable-entry strategy must be distinguished from hierarchical or multilevel models that represent nested data structures.

## 7.4 Categorical response modelling

- Binary response models.
- Multinomial response models.
- Ordinal response models.
- Adjacent-category models.
- Continuation-ratio models.
- Cumulative-link models.
- Log-linear models.
- Multinomial probit models.
- Ordinal probit models.

## 7.5 Regression diagnostics

- Residual analysis.
- Linearity assessment.
- Heteroscedasticity testing.
- Multicollinearity assessment.
- Autocorrelation testing.
- Influence diagnostics.
- Leverage analysis.
- Cook's distance.
- DFBETAs.
- DFFITS.
- Model specification tests.
- Goodness-of-fit assessment.
- Residual normality assessment.
- Calibration assessment.
- Cross-validation.

Cross-validation is primarily a model evaluation procedure, not a substitute for residual or assumption diagnostics.

---

# 8. BAYESIAN STATISTICS

Bayesian statistics is a first-class knowledge area and an inference paradigm that may be applied across multiple statistical domains.

## 8.1 Bayesian foundations

- Prior distributions.
- Likelihood functions.
- Posterior distributions.
- Posterior predictive distributions.
- Bayes' theorem.
- Posterior odds.
- Bayes factors.
- Bayesian decision theory.
- Informative priors.
- Weakly informative priors.
- Non-informative priors.
- Conjugate priors.
- Prior predictive checking.
- Posterior predictive checking.

## 8.2 Bayesian estimation

- Bayesian point estimation.
- Bayesian interval estimation.
- Credible intervals.
- Highest posterior density intervals.
- Conjugate prior analysis.
- Empirical Bayes estimation.
- Hierarchical Bayesian estimation.
- Bayesian model averaging.
- Bayesian shrinkage estimation.
- Bayesian regularisation.

## 8.3 Bayesian hypothesis testing

- Bayesian hypothesis comparison.
- Bayes factors.
- Posterior probability of hypotheses.
- Bayesian evidence assessment.
- Bayesian equivalence testing.
- Bayesian non-inferiority analysis.
- Bayesian model comparison.

## 8.4 Bayesian computational methods

- Markov Chain Monte Carlo.
- Metropolis–Hastings algorithm.
- Gibbs sampling.
- Hamiltonian Monte Carlo.
- No-U-Turn Sampler.
- Importance sampling.
- Sequential Monte Carlo.
- Variational inference.
- Approximate Bayesian computation.
- Posterior predictive checking.
- Convergence diagnostics.
- Effective sample size.
- Trace-plot analysis.
- Monte Carlo standard errors.

## 8.5 Bayesian modelling

- Bayesian linear regression.
- Bayesian logistic regression.
- Bayesian ANOVA.
- Bayesian hierarchical models.
- Bayesian multilevel models.
- Bayesian survival models.
- Bayesian time-series models.
- Bayesian spatial models.
- Bayesian networks.
- Bayesian non-parametric models.
- Bayesian mixture models.
- Bayesian latent-variable models.
- Bayesian causal models.
- Bayesian longitudinal models.

---

# PART V: EXPERIMENTAL DESIGN AND SAMPLING

# 9. EXPERIMENTAL DESIGN AND DESIGN OF EXPERIMENTS

Experimental design is a study-design knowledge area. Its design structures must be distinguished from the statistical procedures used to analyse the resulting data.

## 9.1 Principles of experimental design

- Randomisation.
- Replication.
- Blocking.
- Factorial experimentation.
- Control groups.
- Treatment allocation.
- Experimental units.
- Confounding control.
- Blinding.
- Allocation concealment.
- Treatment fidelity.
- Experimental validity.
- Internal validity.
- External validity.
- Carryover control.
- Interference between experimental units.

## 9.2 Classical experimental designs

- Completely randomised design.
- Randomised complete block design.
- Incomplete block design.
- Balanced incomplete block design.
- Latin square design.
- Graeco-Latin square design.
- Factorial design.
- Full factorial design.
- Fractional factorial design.
- Split-plot design.
- Split-split-plot design.
- Nested design.
- Repeated-measures design.
- Crossover design.
- Incomplete crossover design.
- Response surface designs.

## 9.3 Advanced experimental designs

- Response surface methodology.
- Central composite design.
- Box–Behnken design.
- Mixture design.
- Optimal design.
- D-optimal design.
- A-optimal design.
- G-optimal design.
- I-optimal design.
- Taguchi methods.
- Robust parameter design.
- Sequential experimental design.
- Adaptive experimentation.
- Computer-generated optimal designs.
- Factor screening designs.

## 9.4 Clinical and intervention study designs

- Parallel-group trials.
- Cluster-randomised trials.
- Crossover trials.
- Factorial clinical trials.
- Stepped-wedge trials.
- Adaptive clinical trials.
- Non-inferiority trials.
- Equivalence trials.
- Superiority trials.
- Single-arm trials.
- Pragmatic trials.
- Explanatory trials.
- Platform trials.
- Basket trials.
- Umbrella trials.
- N-of-1 trials.
- Randomised encouragement designs.

## 9.5 Experimental analysis procedures

- Treatment-effect estimation.
- Analysis of variance.
- Blocking analysis.
- Factorial effect analysis.
- Interaction analysis.
- Response surface analysis.
- Sample-size determination.
- Power analysis.
- Interim analysis.
- Multiple-comparison procedures.
- Multiplicity adjustment.
- Treatment-effect heterogeneity analysis.
- Intention-to-treat analysis.
- Per-protocol analysis.
- Sensitivity analysis.

## 9.6 Power and sample-size methods

- Power calculation for means.
- Power calculation for proportions.
- Power calculation for correlations.
- Power calculation for regression.
- Power calculation for ANOVA.
- Cluster-trial sample-size calculation.
- Crossover-trial sample-size calculation.
- Survival-trial sample-size calculation.
- Non-inferiority sample-size calculation.
- Equivalence sample-size calculation.
- Simulation-based power analysis.
- Minimum detectable effect estimation.

---

# 10. SAMPLING AND SURVEY STATISTICS

## 10.1 Probability sampling designs

- Simple random sampling.
- Systematic sampling.
- Stratified random sampling.
- Cluster sampling.
- Multistage sampling.
- Multiphase sampling.
- Probability proportional to size sampling.
- Unequal probability sampling.
- Two-stage sampling.
- Area sampling.
- Adaptive cluster sampling.
- Network sampling.

## 10.2 Non-probability sampling designs

- Convenience sampling.
- Purposive sampling.
- Quota sampling.
- Snowball sampling.
- Respondent-driven sampling.
- Consecutive sampling.
- Volunteer sampling.
- Time-location sampling.
- Venue-based sampling.

Inference from non-probability samples must be clearly distinguished from design-based inference using known inclusion probabilities. Model-based inference requires its own assumptions and justification.

## 10.3 Survey estimation

- Population mean estimation.
- Population total estimation.
- Population proportion estimation.
- Ratio estimation.
- Regression estimation.
- Calibration estimation.
- Horvitz–Thompson estimation.
- Generalised regression estimation.
- Difference estimation.
- Domain estimation.
- Small-area estimation.
- Finite population estimation.

## 10.4 Complex survey analysis

- Survey weights.
- Sampling weights.
- Non-response adjustment.
- Post-stratification.
- Raking.
- Finite population correction.
- Design effects.
- Taylor series linearisation.
- Replicate-weight variance estimation.
- Jackknife variance estimation.
- Balanced repeated replication.
- Bootstrap survey variance estimation.
- Complex-survey regression.
- Complex-survey hypothesis testing.
- Survey-weighted descriptive analysis.
- Survey-weighted confidence intervals.
- Calibration diagnostics.
- Non-response bias assessment.

## 10.5 Sample-size determination

- Estimation-based sample size.
- Hypothesis-testing sample size.
- Power-based sample size.
- Finite population sample size.
- Cluster-adjusted sample size.
- Design-effect-adjusted sample size.
- Non-response-adjusted sample size.
- Precision-based sample size.
- Stratified sample-size allocation.
- Optimal allocation.
- Neyman allocation.
- Simulation-based sample-size determination.

---

# PART VI: MULTIVARIATE AND NON-PARAMETRIC STATISTICS

# 11. MULTIVARIATE STATISTICS

## 11.1 Dimension reduction

- Principal component analysis.
- Exploratory factor analysis.
- Confirmatory factor analysis.
- Independent component analysis.
- Correspondence analysis.
- Multiple correspondence analysis.
- Multidimensional scaling.
- Non-negative matrix factorisation.
- Factor rotation.
- Sparse principal component analysis.
- Kernel principal component analysis.
- Canonical variate analysis.
- Latent-variable analysis.

## 11.2 Multivariate association and modelling

- Canonical correlation analysis.
- Partial least squares.
- Multivariate regression.
- Multivariate analysis of variance.
- Multivariate analysis of covariance.
- Multivariate analysis of repeated measures.
- Multivariate generalised linear models.
- Multivariate analysis of covariance structures.

## 11.3 Classification and discrimination

- Linear discriminant analysis.
- Quadratic discriminant analysis.
- Classification analysis.
- Mahalanobis distance.
- Canonical discriminant analysis.
- Regularised discriminant analysis.
- Multiclass discriminant analysis.

## 11.4 Clustering

- K-means clustering.
- K-medoids clustering.
- Hierarchical clustering.
- Agglomerative clustering.
- Divisive clustering.
- Model-based clustering.
- Gaussian mixture models.
- Fuzzy clustering.
- Density-based clustering.
- DBSCAN.
- Spectral clustering.
- Mean-shift clustering.
- Latent class analysis.
- Latent profile analysis.
- Hierarchical mixture models.

## 11.5 Multivariate distribution analysis

- Multivariate normality assessment.
- Multivariate covariance analysis.
- Multivariate outlier detection.
- Mahalanobis distance analysis.
- Multivariate skewness.
- Multivariate kurtosis.
- Multivariate hypothesis testing.

---

# 12. NON-PARAMETRIC AND DISTRIBUTION-FREE STATISTICS

## 12.1 Non-parametric tests

- Sign test.
- Wilcoxon signed-rank test.
- Mann–Whitney U test.
- Kruskal–Wallis test.
- Friedman test.
- Mood's median test.
- Jonckheere–Terpstra test.
- Spearman correlation.
- Kendall correlation.
- Runs test.
- Kolmogorov–Smirnov test.
- Cramér–von Mises test.

## 12.2 Randomisation and permutation methods

- Permutation tests.
- Randomisation tests.
- Exact randomisation inference.
- Permutation correlation tests.
- Permutation regression tests.
- Permutation-based ANOVA.
- Restricted permutation procedures.

## 12.3 Non-parametric estimation and modelling

- Kernel density estimation.
- Non-parametric regression.
- Local polynomial regression.
- Smoothing splines.
- Quantile-based inference.
- Distribution-free confidence intervals.
- Rank-based estimation.
- Empirical distribution estimation.
- Non-parametric hazard estimation.

## 12.4 Robust statistical methods

- Robust location estimation.
- Robust scale estimation.
- Robust regression.
- M-estimation.
- R-estimation.
- L-estimation.
- Winsorisation.
- Trimmed estimators.
- Robust covariance estimation.
- Robust correlation.
- Robust multivariate analysis.

---

# PART VII: TIME, SURVIVAL AND LONGITUDINAL STATISTICS

# 13. TIME-SERIES ANALYSIS AND FORECASTING

## 13.1 Time-series exploration

- Trend analysis.
- Seasonal analysis.
- Cyclical analysis.
- Autocorrelation.
- Partial autocorrelation.
- Decomposition.
- Moving averages.
- Exponential smoothing.
- Structural-break analysis.
- Seasonal decomposition.
- Time-series visualisation.

## 13.2 Stationarity and diagnostics

- Augmented Dickey–Fuller test.
- Phillips–Perron test.
- KPSS test.
- Ljung–Box test.
- Box–Pierce test.
- Unit-root testing.
- Residual diagnostics.
- Structural-break testing.
- Change-point detection.
- ARCH effect testing.

## 13.3 Time-series models

- Autoregressive models.
- Moving-average models.
- ARMA.
- ARIMA.
- Seasonal ARIMA.
- Vector autoregression.
- Vector error-correction models.
- ARCH.
- GARCH.
- Exponential smoothing state-space models.
- State-space models.
- Structural time-series models.
- Dynamic factor models.
- Regime-switching models.
- Threshold autoregressive models.
- Distributed-lag models.
- Autoregressive distributed-lag models.
- Fractionally integrated models.
- Long-memory models.
- Cointegration models.
- Functional time-series models.

## 13.4 Volatility and financial time series

- ARCH models.
- GARCH models.
- EGARCH.
- GJR-GARCH.
- Multivariate GARCH.
- Stochastic volatility models.
- Realised volatility models.
- Volatility forecasting.

## 13.5 Spectral and frequency-domain methods

- Spectral analysis.
- Periodogram analysis.
- Cross-spectral analysis.
- Fourier methods.
- Wavelet analysis.
- Frequency-domain estimation.

## 13.6 Forecasting

- Naive forecasting.
- Seasonal naive forecasting.
- Exponential smoothing.
- Holt's method.
- Holt–Winters method.
- ARIMA forecasting.
- Regression-based forecasting.
- Probabilistic forecasting.
- Forecast intervals.
- Forecast accuracy assessment.
- Hierarchical forecasting.
- Reconciliation of forecasts.
- Ensemble forecasting.

---

# 14. SURVIVAL AND EVENT-HISTORY ANALYSIS

## 14.1 Survival estimation

- Kaplan–Meier estimator.
- Nelson–Aalen estimator.
- Life-table analysis.
- Survival probability estimation.
- Cumulative hazard estimation.
- Restricted mean survival time.

## 14.2 Survival hypothesis testing

- Log-rank test.
- Wilcoxon–Breslow–Gehan test.
- Tarone–Ware test.
- Tests for equality of survival curves.

## 14.3 Survival models

- Cox proportional hazards regression.
- Stratified Cox regression.
- Time-dependent Cox regression.
- Parametric survival regression.
- Weibull survival models.
- Exponential survival models.
- Log-normal survival models.
- Log-logistic survival models.
- Generalised gamma survival models.
- Accelerated failure-time models.
- Frailty models.
- Flexible parametric survival models.

## 14.4 Advanced event-history methods

- Competing-risks analysis.
- Fine–Gray regression.
- Cause-specific hazard modelling.
- Recurrent-event analysis.
- Multi-state models.
- Joint longitudinal-survival models.
- Cure models.
- Interval-censored survival analysis.
- Left-truncated survival analysis.
- Recurrent-event frailty models.

## 14.5 Survival measures and diagnostics

- Hazard ratio estimation.
- Survival probability estimation.
- Cumulative incidence functions.
- Proportional hazards diagnostics.
- Schoenfeld residuals.
- Martingale residuals.
- Deviance residuals.
- Survival model calibration.
- Time-dependent ROC analysis.

---

# 15. LONGITUDINAL AND REPEATED-MEASURES STATISTICS

Longitudinal analysis deals with repeated observations over time, usually involving the same individuals, units or clusters.

## 15.1 Longitudinal data structures

- Repeated-measures data.
- Panel data.
- Clustered longitudinal data.
- Individual growth trajectories.
- Unequally spaced longitudinal data.
- Unbalanced longitudinal data.
- Longitudinal cohort data.

## 15.2 Longitudinal models

- Repeated-measures ANOVA.
- Linear mixed-effects models.
- Generalised linear mixed models.
- Multilevel longitudinal models.
- Growth-curve models.
- Latent growth models.
- Generalised estimating equations.
- Marginal models.
- Random-intercept models.
- Random-slope models.
- Joint longitudinal models.
- Bayesian longitudinal models.

## 15.3 Longitudinal analysis procedures

- Within-subject comparisons.
- Between-subject comparisons.
- Time-by-group interaction analysis.
- Trajectory analysis.
- Change-score analysis.
- Baseline-adjusted analysis.
- Longitudinal treatment-effect estimation.
- Missing longitudinal data analysis.
- Longitudinal mediation analysis.

## 15.4 Longitudinal diagnostics

- Residual diagnostics.
- Covariance structure assessment.
- Random-effects diagnostics.
- Serial correlation assessment.
- Model fit assessment.
- Sensitivity analysis.

---

# PART VIII: SPATIAL, CAUSAL AND STOCHASTIC STATISTICS

# 16. SPATIAL STATISTICS AND GEOSTATISTICS

## 16.1 Spatial exploration

- Spatial distribution analysis.
- Spatial point-pattern analysis.
- Spatial clustering.
- Spatial density estimation.
- Kernel density mapping.
- Spatial autocorrelation.
- Spatial data visualisation.
- Spatial outlier detection.

## 16.2 Spatial dependence

- Global Moran's I.
- Local Moran's I.
- Geary's C.
- Getis–Ord Gi*.
- Spatial correlograms.
- Join-count statistics.
- Spatial scan statistics.

## 16.3 Spatial modelling

- Spatial autoregressive models.
- Spatial error models.
- Spatial Durbin models.
- Conditional autoregressive models.
- Simultaneous autoregressive models.
- Spatial generalised linear mixed models.
- Spatial Bayesian models.
- Geographically weighted regression.
- Spatial panel models.
- Spatial lag models.
- Spatial probit models.
- Disease-mapping models.

## 16.4 Geostatistics

- Variograms.
- Semivariograms.
- Kriging.
- Ordinary kriging.
- Universal kriging.
- Co-kriging.
- Spatial interpolation.
- Gaussian processes.
- Indicator kriging.
- Block kriging.

## 16.5 Spatial point processes

- Poisson point processes.
- Inhomogeneous Poisson processes.
- Cox processes.
- Cluster point processes.
- Marked point processes.
- Spatial interaction analysis.

## 16.6 Spatiotemporal statistics

- Spatiotemporal point processes.
- Spatiotemporal regression.
- Spatiotemporal disease mapping.
- Dynamic spatial models.
- Spatial-temporal Bayesian models.
- Spatiotemporal forecasting.

---

# 17. CAUSAL INFERENCE

## 17.1 Causal foundations

- Potential outcomes framework.
- Counterfactual inference.
- Directed acyclic graphs.
- Structural causal models.
- Confounding assessment.
- Identification assumptions.
- Consistency.
- Exchangeability.
- Positivity.
- Interference.
- Average treatment effect.
- Average treatment effect on the treated.
- Average treatment effect on the untreated.
- Conditional average treatment effect.
- Heterogeneous treatment effects.
- Causal estimands.

## 17.2 Experimental causal methods

- Randomised controlled trials.
- Cluster-randomised experiments.
- Factorial experiments.
- Instrumented randomisation.
- Randomised encouragement designs.
- Treatment assignment analysis.
- Intention-to-treat estimation.
- Per-protocol estimation.

## 17.3 Observational causal methods

- Propensity-score matching.
- Propensity-score weighting.
- Inverse probability weighting.
- Regression adjustment.
- Doubly robust estimation.
- Difference-in-differences.
- Instrumental-variable estimation.
- Regression discontinuity design.
- Synthetic control.
- Interrupted time-series analysis.
- Matching methods.
- Mediation analysis.
- Moderation analysis.
- Sensitivity analysis for unmeasured confounding.
- Targeted maximum likelihood estimation.
- G-computation.
- Marginal structural models.
- Longitudinal causal models.
- Negative-control methods.

## 17.4 Advanced causal methods

- Instrumental-variable identification.
- Principal stratification.
- Mediation estimands.
- Interventional direct and indirect effects.
- Transportability.
- Generalisability of causal effects.
- Causal discovery.
- Causal machine learning.
- Double/debiased machine learning.
- Causal forests.
- Heterogeneous treatment-effect estimation.
- Sensitivity analysis for violations of identification assumptions.

## 17.5 Causal diagnostics and validation

- Covariate balance assessment.
- Positivity assessment.
- Overlap diagnostics.
- Instrument strength assessment.
- Regression discontinuity validity checks.
- Parallel-trends assessment.
- Sensitivity analysis.
- Robustness checks.
- Negative-control analysis.

---

# 18. STOCHASTIC PROCESSES

## 18.1 Discrete stochastic processes

- Markov chains.
- Discrete-time Markov chains.
- Markov decision processes.
- Branching processes.
- Random walks.
- Birth–death processes.
- Renewal processes.
- Discrete-state stochastic processes.

## 18.2 Continuous stochastic processes

- Markov processes.
- Continuous-time Markov chains.
- Poisson processes.
- Brownian motion.
- Wiener processes.
- Gaussian processes.
- Martingales.
- Stochastic differential equations.
- Diffusion processes.
- Lévy processes.

## 18.3 Applied stochastic processes

- Queueing theory.
- Reliability stochastic processes.
- Epidemic stochastic processes.
- Population processes.
- Inventory processes.
- Spatial stochastic processes.
- Financial stochastic processes.

## 18.4 Stochastic modelling

- Transition probability estimation.
- Stationary distribution estimation.
- First-passage time analysis.
- Absorbing-state analysis.
- Stochastic simulation.
- Stochastic optimisation.

---

# PART IX: SPECIALISED STATISTICAL DISCIPLINES

# 19. RELIABILITY AND QUALITY STATISTICS

## 19.1 Reliability analysis

- Reliability functions.
- Failure-time distributions.
- Mean time to failure.
- Mean time between failures.
- Hazard functions.
- System reliability.
- Series-system reliability.
- Parallel-system reliability.
- Accelerated life testing.
- Reliability growth modelling.
- Repairable-system analysis.
- Recurrent failure analysis.
- Component reliability.
- System availability.

## 19.2 Statistical quality control

- Statistical process control.
- Shewhart control charts.
- X-bar charts.
- R charts.
- S charts.
- p charts.
- np charts.
- c charts.
- u charts.
- CUSUM charts.
- EWMA charts.
- Multivariate control charts.
- Process capability analysis.
- Process performance analysis.
- Acceptance sampling.
- Six Sigma statistical methods.
- Process monitoring.
- Change detection.

## 19.3 Quality and reliability modelling

- Reliability block diagrams.
- Fault-tree analysis.
- Failure-mode analysis.
- Degradation modelling.
- Accelerated degradation modelling.
- Warranty analysis.
- Competing failure modes.

---

# 20. EPIDEMIOLOGICAL AND BIOSTATISTICAL METHODS

## 20.1 Disease frequency

- Incidence.
- Incidence rate.
- Cumulative incidence.
- Prevalence.
- Point prevalence.
- Period prevalence.
- Mortality rate.
- Case-fatality proportion.
- Standardised mortality ratios.
- Standardised incidence ratios.
- Age-specific rates.
- Person-time analysis.

## 20.2 Measures of association and impact

- Risk ratio.
- Rate ratio.
- Odds ratio.
- Prevalence ratio.
- Risk difference.
- Attributable risk.
- Population attributable fraction.
- Number needed to treat.
- Number needed to harm.
- Vaccine effectiveness.
- Standardised rate ratios.

## 20.3 Epidemiological study analysis

- Cohort analysis.
- Case-control analysis.
- Cross-sectional analysis.
- Ecological analysis.
- Outbreak analysis.
- Stratified analysis.
- Direct standardisation.
- Indirect standardisation.
- Mantel–Haenszel analysis.
- Diagnostic test accuracy.
- Sensitivity and specificity.
- Positive and negative predictive values.
- Likelihood ratios.
- ROC curve analysis.
- Meta-analysis of epidemiological studies.

## 20.4 Clinical and biomedical statistics

- Clinical trial analysis.
- Repeated-measures biomedical analysis.
- Diagnostic accuracy studies.
- Agreement analysis.
- Bland–Altman analysis.
- Bioequivalence analysis.
- Dose-response modelling.
- Pharmacokinetic modelling.
- Pharmacodynamic modelling.
- Longitudinal clinical analysis.
- Biomarker analysis.
- Reference interval estimation.
- Diagnostic threshold analysis.

## 20.5 Infectious-disease modelling

- Compartmental models.
- SIR models.
- SIS models.
- SEIR models.
- Stochastic epidemic models.
- Reproduction number estimation.
- Epidemic growth-rate estimation.
- Transmission-rate estimation.
- Outbreak forecasting.
- Infectious-disease survival analysis.
- Spatial epidemic modelling.
- Vaccination-impact modelling.

## 20.6 Population and public-health analysis

- Demographic rate analysis.
- Fertility analysis.
- Mortality analysis.
- Life-table methods.
- Standardised mortality analysis.
- Health-service utilisation analysis.
- Screening evaluation.
- Health inequality analysis.
- Population attributable risk.
- Health programme evaluation.
- Disease burden estimation.

## 20.7 Biostatistical model extensions

- Multilevel health models.
- Clustered health-outcome models.
- Bayesian disease models.
- Spatial disease models.
- Longitudinal clinical models.
- Joint models of biomarkers and survival.
- Diagnostic prediction models.

---

# 21. PSYCHOMETRICS AND MEASUREMENT THEORY

## 21.1 Classical test theory

- Classical test theory.
- True-score theory.
- Measurement error.
- Reliability coefficients.
- Cronbach's alpha.
- McDonald's omega.
- Split-half reliability.
- Test–retest reliability.
- Inter-rater reliability.
- Intraclass correlation coefficient.

## 21.2 Item response theory

- One-parameter logistic model.
- Two-parameter logistic model.
- Three-parameter logistic model.
- Graded response model.
- Partial credit model.
- Rating scale model.
- Nominal response model.
- Item characteristic curves.
- Item information functions.
- Test information functions.

## 21.3 Rasch measurement

- Rasch model.
- Rating scale Rasch model.
- Partial credit Rasch model.
- Person ability estimation.
- Item difficulty estimation.
- Fit statistics.
- Differential item functioning.

## 21.4 Measurement validity

- Measurement validity.
- Construct validity.
- Content validity.
- Criterion validity.
- Convergent validity.
- Discriminant validity.
- Predictive validity.
- Measurement invariance.
- Differential item functioning.
- Cross-cultural measurement equivalence.

## 21.5 Scale development and assessment

- Scale development.
- Item generation.
- Item analysis.
- Exploratory factor analysis.
- Confirmatory factor analysis.
- Reliability assessment.
- Validity assessment.
- Factor structure assessment.
- Generalisability theory.
- Latent-variable measurement models.

---

# 22. STATISTICAL LEARNING AND PREDICTIVE MODELLING

## 22.1 Supervised learning

- Linear regression.
- Logistic regression.
- Decision trees.
- Random forests.
- Gradient boosting.
- Extreme gradient boosting.
- Support vector machines.
- K-nearest neighbours.
- Naive Bayes.
- Classification algorithms.
- Regression algorithms.
- Generalised additive models.
- Penalised regression.

## 22.2 Unsupervised learning

- Clustering.
- Dimension reduction.
- Principal component analysis.
- Factor analysis.
- Anomaly detection.
- Association-rule mining.
- Density estimation.
- Latent class analysis.
- Manifold learning.

## 22.3 Model evaluation

- Train-test splitting.
- Cross-validation.
- Bootstrap validation.
- Confusion matrix.
- Accuracy.
- Precision.
- Recall.
- Specificity.
- F1 score.
- ROC curve.
- Area under the ROC curve.
- Precision–recall curve.
- Calibration analysis.
- Brier score.
- Regression prediction errors.
- Mean absolute error.
- Mean squared error.
- Root mean squared error.
- Mean absolute percentage error.
- Bias–variance assessment.
- External validation.
- Temporal validation.
- Geographic validation.

## 22.4 Advanced learning methods

- Regularisation.
- Ensemble learning.
- Stacking.
- Bagging.
- Boosting.
- Feature selection.
- Feature importance.
- Model interpretability.
- Partial dependence.
- SHAP analysis.
- Survival machine learning.
- Imbalanced classification methods.
- Cost-sensitive learning.
- Transfer learning.
- Semi-supervised learning.
- Active learning.

## 22.5 Predictive model reliability

- Model calibration.
- Prediction uncertainty.
- Decision-curve analysis.
- Net benefit analysis.
- External validation.
- Model drift assessment.
- Subgroup performance assessment.
- Fairness assessment.
- Explainability limitations.
- Generalisability assessment.

---

# PART X: ADVANCED AND EXTENDED STATISTICAL DOMAINS

# 23. EXTREME-VALUE STATISTICS

- Extreme-value theory.
- Generalised extreme-value distribution.
- Generalised Pareto distribution.
- Block maxima methods.
- Peaks-over-threshold methods.
- Return-level estimation.
- Return-period estimation.
- Tail-index estimation.
- Extreme quantile estimation.
- Multivariate extreme-value analysis.
- Extreme-value regression.
- Tail dependence analysis.

# 24. COMPOSITIONAL DATA ANALYSIS

- Compositional data structures.
- Closure operation.
- Simplex geometry.
- Log-ratio transformations.
- Additive log-ratio transformation.
- Centred log-ratio transformation.
- Isometric log-ratio transformation.
- Compositional correlation.
- Compositional regression.
- Compositional principal component analysis.
- Compositional clustering.
- Zero replacement methods.
- Compositional data visualisation.

# 25. FUNCTIONAL DATA ANALYSIS

- Functional data representation.
- Functional data exploration.
- Functional principal component analysis.
- Functional regression.
- Functional linear models.
- Functional logistic regression.
- Functional clustering.
- Functional classification.
- Functional time-series analysis.
- Smoothing and basis representation.
- Functional covariance analysis.
- Functional data visualisation.

# 26. DIRECTIONAL AND CIRCULAR STATISTICS

- Circular data representation.
- Directional distributions.
- Von Mises distribution.
- Circular mean.
- Circular variance.
- Circular dispersion.
- Circular correlation.
- Circular regression.
- Tests for uniformity.
- Rayleigh test.
- Watson's test.
- Kuiper's test.
- Directional data visualisation.

# 27. NETWORK STATISTICS

- Network data structures.
- Graph-theoretic measures.
- Degree distribution.
- Centrality measures.
- Network density.
- Clustering coefficients.
- Community detection.
- Exponential random graph models.
- Stochastic block models.
- Network regression.
- Relational event models.
- Network sampling.
- Network dependence modelling.
- Social network analysis.

# 28. INFORMATION THEORY AND INFORMATION-BASED STATISTICS

- Shannon entropy.
- Conditional entropy.
- Mutual information.
- Kullback–Leibler divergence.
- Jensen–Shannon divergence.
- Information gain.
- Cross-entropy.
- Minimum description length.
- Information criteria.
- Akaike information criterion.
- Bayesian information criterion.
- Model information assessment.

# 29. ECONOMETRICS AND FINANCIAL STATISTICS

- Cross-sectional econometrics.
- Time-series econometrics.
- Panel-data econometrics.
- Fixed-effects estimation.
- Random-effects estimation.
- Instrumental-variable estimation.
- Two-stage least squares.
- Generalised method of moments.
- Simultaneous-equation models.
- Cointegration.
- Error-correction models.
- Dynamic panel models.
- Volatility models.
- Financial risk modelling.
- Value-at-risk estimation.
- Expected shortfall estimation.
- Financial dependence modelling.

---

# PART XI: CROSS-CUTTING STATISTICAL CAPABILITIES

# 30. EFFECT-SIZE ESTIMATION AND MEASURES OF ASSOCIATION

Effect sizes quantify the magnitude of differences, relationships or effects. They must be distinguished from test statistics, p-values and model parameters.

## 30.1 Standardised mean differences

- Cohen's d.
- Hedges' g.
- Glass's delta.
- Common-language effect size.
- Standardised mean difference.

## 30.2 ANOVA effect sizes

- Eta-squared.
- Partial eta-squared.
- Omega-squared.
- Partial omega-squared.
- Cohen's f.

## 30.3 Association effect sizes

- Pearson's r.
- Phi coefficient.
- Cramér's V.
- Rank-biserial correlation.
- Kendall's tau.
- Spearman's rho.
- Contingency coefficient.

## 30.4 Epidemiological and clinical effect measures

- Odds ratio.
- Risk ratio.
- Rate ratio.
- Risk difference.
- Prevalence ratio.
- Incidence-rate ratio.
- Hazard ratio.
- Number needed to treat.
- Number needed to harm.
- Attributable fraction.
- Population attributable fraction.

## 30.5 Regression and predictive measures

- Regression coefficients.
- Standardised regression coefficients.
- R-squared.
- Adjusted R-squared.
- Partial R-squared.
- Prediction error measures.
- Explained variance.
- Model discrimination measures.

## 30.6 Reporting principles

Each effect-size record should identify:

- Its mathematical definition.
- Its applicable statistical method.
- Its scale and interpretation.
- Whether it is standardised or unstandardised.
- Its uncertainty estimate.
- Its limitations.
- Whether directionality is meaningful.

Odds ratios, hazard ratios and regression coefficients should not automatically be labelled standardised effect sizes.

---

# 31. ASSUMPTION TESTING AND STATISTICAL DIAGNOSTICS

Diagnostics are supporting analytical procedures. They are not automatically primary research analyses.

## 31.1 Distributional diagnostics

- Shapiro–Wilk test.
- Anderson–Darling test.
- Kolmogorov–Smirnov test.
- Lilliefors test.
- Jarque–Bera test.
- Q–Q plot assessment.
- P–P plot assessment.
- Skewness assessment.
- Kurtosis assessment.
- Multivariate normality assessment.

## 31.2 Variance and dependence diagnostics

- Levene's test.
- Brown–Forsythe test.
- Bartlett's test.
- Fligner–Killeen test.
- Durbin–Watson test.
- Breusch–Pagan test.
- White's test.
- Breusch–Godfrey test.
- Autocorrelation assessment.
- Heteroscedasticity assessment.

## 31.3 Regression diagnostics

- Variance inflation factor.
- Tolerance.
- Residual analysis.
- Cook's distance.
- Leverage.
- DFBETAs.
- DFFITS.
- Ramsey RESET test.
- Influence analysis.
- Specification diagnostics.
- Residual normality assessment.
- Functional-form assessment.

## 31.4 Model-specific diagnostics

- Proportional hazards assessment.
- Schoenfeld residual analysis.
- Survival model calibration.
- Generalised linear model deviance diagnostics.
- Overdispersion assessment.
- Zero-inflation assessment.
- Mixed-model residual assessment.
- Random-effects diagnostics.
- Time-series residual diagnostics.
- Spatial residual diagnostics.
- Bayesian convergence diagnostics.
- Posterior predictive checks.

## 31.5 General data diagnostics

- Missing-data analysis.
- Missingness-pattern analysis.
- Outlier detection.
- Duplicate detection.
- Data consistency checks.
- Data validity checks.
- Distributional anomaly detection.
- Range checks.
- Logical consistency checks.
- Unit and scale checks.
- Sampling-weight validation.
- Record linkage checks.

## 31.6 Missingness mechanisms

- Missing completely at random (MCAR).
- Missing at random (MAR).
- Missing not at random (MNAR).

These are conceptual missingness mechanisms. They must not be presented as categories that can always be conclusively established from observed data alone.

Little's MCAR test and other diagnostic procedures may provide evidence relevant to missingness assessment, but do not prove that MAR or MNAR holds.

---

# 32. RESAMPLING, SIMULATION AND COMPUTATIONAL INFERENCE

These are cross-cutting computational capabilities that may support multiple statistical methods.

## 32.1 Bootstrap procedures

- Bootstrap.
- Parametric bootstrap.
- Non-parametric bootstrap.
- Cluster bootstrap.
- Block bootstrap.
- Stratified bootstrap.
- Wild bootstrap.
- Bayesian bootstrap.
- Bootstrap confidence intervals.
- Bootstrap standard errors.
- Bootstrap bias estimation.

## 32.2 Permutation and randomisation procedures

- Permutation testing.
- Randomisation inference.
- Exact permutation procedures.
- Restricted permutation.
- Permutation-based confidence procedures.

## 32.3 Simulation methods

- Monte Carlo simulation.
- Stochastic simulation.
- Simulation-based power analysis.
- Simulation-based sample-size determination.
- Statistical uncertainty propagation.
- Sensitivity simulation.
- Scenario simulation.

## 32.4 Computational algorithms

- Markov Chain Monte Carlo.
- Importance sampling.
- Rejection sampling.
- Sequential Monte Carlo.
- Numerical integration.
- Numerical optimisation.
- Variational inference.
- Approximate Bayesian computation.
- Gibbs sampling.
- Metropolis–Hastings.
- Hamiltonian Monte Carlo.
- No-U-Turn Sampler.

## 32.5 Computational validation

- Numerical convergence assessment.
- Monte Carlo error assessment.
- Simulation validation.
- Reproducibility checks.
- Algorithm stability assessment.
- Computational precision assessment.

---

# 33. META-ANALYSIS AND EVIDENCE SYNTHESIS

## 33.1 Meta-analysis models

- Fixed-effect meta-analysis.
- Random-effects meta-analysis.
- Multilevel meta-analysis.
- Network meta-analysis.
- Pairwise meta-analysis.
- Proportional meta-analysis.
- Meta-regression.
- Individual participant data meta-analysis.
- Bayesian meta-analysis.

## 33.2 Heterogeneity analysis

- Cochran's Q.
- I-squared statistic.
- Tau-squared.
- Prediction intervals.
- Between-study variance estimation.
- Subgroup analysis.
- Meta-regression.
- Heterogeneity sensitivity analysis.

## 33.3 Publication bias and small-study effects

- Funnel plots.
- Egger's test.
- Begg's test.
- Trim-and-fill method.
- Selection models.
- Sensitivity analysis for publication bias.

## 33.4 Evidence synthesis procedures

- Leave-one-out sensitivity analysis.
- Cumulative meta-analysis.
- Systematic-review statistical synthesis.
- Evidence grading support.
- Risk-of-bias integration.
- Network evidence synthesis.
- Evidence certainty assessment.

---

# 34. MISSING-DATA STATISTICS

## 34.1 Missing-data assessment

- Missingness identification.
- Missingness-pattern analysis.
- Missingness-mechanism assessment.
- MCAR assessment.
- MAR assumptions.
- MNAR assumptions.
- Missing-data sensitivity analysis.

## 34.2 Complete and available case methods

- Complete-case analysis.
- Available-case analysis.
- Pairwise deletion.
- Listwise deletion.

## 34.3 Single imputation

- Mean imputation.
- Median imputation.
- Mode imputation.
- Regression imputation.
- Hot-deck imputation.
- Predictive mean matching.

Single imputation methods should be accompanied by warnings about their limitations, particularly the potential understatement of uncertainty.

## 34.4 Multiple imputation and likelihood methods

- Multiple imputation.
- Multiple imputation by chained equations.
- Joint-model multiple imputation.
- Multilevel multiple imputation.
- Multiple imputation for categorical data.
- Maximum likelihood estimation with missing data.
- Full-information maximum likelihood.
- Inverse probability weighting for missingness.

## 34.5 MNAR sensitivity analysis

- Pattern-mixture models.
- Selection models.
- Shared-parameter models.
- Delta-adjustment sensitivity analysis.
- Tipping-point analysis.
- Sensitivity analysis for missing-not-at-random mechanisms.

---

# PART XII: STATISTICAL REPORTING, VISUALISATION AND SOFTWARE ARCHITECTURE

# 35. STATISTICAL REPORTING

Every applicable analysis should support structured reporting.

## 35.1 Research context

- Research objective.
- Research question.
- Research hypothesis.
- Study design.
- Population of interest.
- Sampling design.
- Statistical domain.
- Analytical purpose.

## 35.2 Data description

- Dataset identification.
- Sample size.
- Analytical sample size.
- Variable definitions.
- Variable roles.
- Measurement scales.
- Data exclusions.
- Missing-data handling.
- Data transformations.
- Data-quality findings.

## 35.3 Method selection

- Selected method.
- Method-selection rationale.
- Alternative methods considered.
- Method assumptions.
- Suitability of data.
- Statistical model specification.
- Estimand.

## 35.4 Statistical results

- Descriptive summaries.
- Test statistic or model estimates.
- Degrees of freedom, where applicable.
- P-value, where applicable.
- Confidence interval or credible interval, where applicable.
- Effect size, where applicable.
- Standard errors.
- Model-fit statistics.
- Diagnostic findings.
- Prediction measures, where applicable.

## 35.5 Interpretation

- Statistical interpretation.
- Practical interpretation.
- Clinical or programme interpretation, where relevant.
- Magnitude and direction of effects.
- Uncertainty.
- Limitations.
- Assumption violations.
- Sensitivity analysis.
- Reproducibility information.

## 35.6 Reporting standards

TimanStat should support appropriate reporting structures for different disciplines and study designs.

It should not impose a single reporting template on all statistical analyses.

---

# 36. VISUALISATION AND PRESENTATION

## 36.1 Descriptive visualisations

- Bar charts.
- Histograms.
- Box plots.
- Violin plots.
- Density plots.
- Frequency polygons.
- Scatter plots.
- Line charts.
- Heatmaps.
- Mosaic plots.
- Population pyramids.
- Pareto charts.

## 36.2 Inferential visualisations

- Confidence-interval plots.
- Forest plots.
- Effect-size plots.
- Coefficient plots.
- Hypothesis comparison plots.
- Sampling-distribution plots.
- Posterior distribution plots.
- Posterior predictive plots.

## 36.3 Model diagnostics and evaluation

- Regression diagnostic plots.
- Residual plots.
- Q–Q plots.
- Influence plots.
- Calibration plots.
- ROC curves.
- Precision–recall curves.
- Decision curves.
- Partial dependence plots.
- Variable importance plots.

## 36.4 Specialised visualisations

- Survival curves.
- Kaplan–Meier plots.
- Competing-risk plots.
- Spatial maps.
- Time-series plots.
- Forecast plots.
- Control charts.
- Meta-analysis funnel plots.
- Network graphs.
- Circular plots.
- Functional data plots.
- Compositional data plots.

---

# 37. STATISTICAL METHOD METADATA AND MACHINE-READABLE REGISTRY

Every catalogue entity should have a structured machine-readable record.

The metadata system must distinguish the entity's identity, classification, analytical requirements, computational availability and verification status.

## 37.1 Core identity fields

- `entity_id` — globally unique identifier.
- `name` — human-readable name.
- `entity_type` — method, model, design, diagnostic, algorithm, measure, visualisation, principle or reporting procedure.
- `description` — concise methodological description.
- `version` — catalogue or entity version.
- `parent_id` — parent entity, where applicable.
- `related_entity_ids` — related canonical records.
- `aliases` — alternative names and abbreviations.

## 37.2 Classification fields

- `knowledge_area` — primary statistical knowledge area.
- `knowledge_area_tags` — additional relevant areas.
- `analysis_purpose` — descriptive, exploratory, inferential, predictive, causal or decision-oriented.
- `method_family` — method family.
- `inference_paradigm` — frequentist, Bayesian, randomisation-based, likelihood-based or not applicable.
- `application_domains` — epidemiology, agriculture, education, economics, public health and other areas.
- `classification_tags` — additional searchable labels.

## 37.3 Research-question fields

- `research_objectives` — objectives addressed.
- `research_question_patterns` — natural-language question patterns.
- `hypothesis_requirements` — whether formal hypotheses are required.
- `estimand` — target quantity being estimated.
- `interpretation_framework` — relevant interpretation rules.

## 37.4 Variable and data requirements

- `variable_requirements` — outcome, predictor, factor, covariate and other roles.
- `measurement_scales` — nominal, ordinal, interval and ratio.
- `data_structure_requirements` — independent, paired, clustered, repeated, longitudinal, time-series, spatial or other structures.
- `outcome_type` — continuous, binary, categorical, count, ordinal, time-to-event or other.
- `sample_size_requirements` — applicable minimum or recommended sample considerations.
- `sampling_design_requirements` — relevant sampling requirements.
- `study_design_requirements` — relevant research-design requirements.
- `weighting_requirements` — whether sampling or other weights are required.
- `missing_data_requirements` — handling considerations.

## 37.5 Statistical specification fields

- `model_specification` — formal model structure.
- `variable_roles` — required and optional roles.
- `assumptions` — method-specific assumptions.
- `selection_rules` — conditions for method recommendation.
- `exclusion_rules` — conditions under which the method should not be recommended.
- `alternative_methods` — alternatives.
- `related_diagnostics` — diagnostic entity identifiers.
- `related_effect_sizes` — applicable effect-size identifiers.
- `related_intervals` — applicable uncertainty-interval procedures.

## 37.6 Computational fields

- `computational_requirements` — computational resources or dependencies.
- `algorithm_ids` — computational algorithms used.
- `numerical_requirements` — optimisation, integration or convergence requirements.
- `execution_constraints` — limits and restrictions.
- `supported_data_types` — data formats or structures supported.
- `output_schema` — expected result structure.

## 37.7 Result and reporting fields

- `outputs` — statistics, estimates and model outputs.
- `effect_sizes` — applicable effect-size measures.
- `interval_estimates` — applicable confidence or credible intervals.
- `diagnostics` — applicable diagnostic procedures.
- `limitations` — known methodological limitations.
- `interpretation_guidance` — rules for explaining findings.
- `visualisation_ids` — recommended visualisation entities.
- `reporting_requirements` — required reporting elements.

## 37.8 Implementation and verification fields

- `recognition_status` — whether TimanStat can identify the entity.
- `recommendation_status` — whether TimanStat can recommend it.
- `specification_status` — whether TimanStat can construct its analytical specification.
- `implementation_status` — computational development state.
- `testing_status` — test coverage and execution state.
- `verification_status` — methodological and numerical verification state.
- `validation_status` — validation against accepted references, benchmarks or independent implementations.
- `last_verified` — date of last verification.
- `references` — authoritative methodological sources.

## 37.9 Relationship fields

- `parent_id` — parent entity.
- `related_entity_ids` — related entities.
- `requires_entity_ids` — required supporting entities.
- `diagnostic_entity_ids` — relevant diagnostics.
- `algorithm_entity_ids` — relevant computational algorithms.
- `design_entity_ids` — relevant study designs.
- `alternative_entity_ids` — alternative procedures.

## 37.10 Example conceptual record

The following is an illustrative record for Welch's independent-samples t-test. It is a schema example, not a claim that every field has already been implemented.

```json
{
  "entity_id": "method.inference.mean_difference.welch_t_test",
  "name": "Welch's independent-samples t-test",
  "entity_type": "method",
  "knowledge_area": "frequentist_inference",
  "analysis_purpose": ["inferential"],
  "inference_paradigm": ["frequentist"],
  "method_family": "difference_testing",
  "research_objectives": [
    "Compare the means of two independent groups"
  ],
  "estimand": "Difference between population means",
  "outcome_type": "continuous",
  "data_structure_requirements": [
    "two independent groups"
  ],
  "assumptions": [
    "independent observations",
    "appropriate continuous outcome",
    "finite group variances"
  ],
  "related_diagnostics": [],
  "implementation_status": "implemented",
  "testing_status": "to_be_verified",
  "verification_status": "to_be_verified",
  "validation_status": "to_be_verified"
}
```

The status values in an actual registry must be based on verified project evidence, not copied from this illustrative example.

---

# 38. IMPLEMENTATION, TESTING, VERIFICATION AND VALIDATION STATUS

Catalogue inclusion and operational availability must remain separate.

## 38.1 Recognition status

- `not_registered`
- `registered`
- `recognised`

Indicates whether the platform has a formal knowledge record and can identify the entity.

## 38.2 Recommendation status

- `not_available`
- `under_development`
- `available`

Indicates whether the analysis planner can recommend the method appropriately.

## 38.3 Specification status

- `not_available`
- `under_development`
- `available`

Indicates whether TimanStat can construct a valid analytical specification for the method.

## 38.4 Implementation status

- `planned`
- `in_development`
- `implemented`

Indicates the computational development state.

## 38.5 Testing status

- `not_tested`
- `tests_in_development`
- `tested`

Indicates whether automated tests have been written and executed successfully.

## 38.6 Verification status

- `not_verified`
- `verification_in_progress`
- `verified`

Indicates whether calculations and outputs have been checked against accepted mathematical or statistical references.

## 38.7 Validation status

- `not_validated`
- `validation_in_progress`
- `validated`

Indicates whether the implementation has been evaluated against appropriate benchmarks, independent implementations, reference datasets or other accepted validation procedures.

## 38.8 Operational eligibility

A method must not be presented as fully operational merely because its code exists.

Operational eligibility should require:

1. A registered canonical entity.
2. An appropriate analytical specification.
3. Implemented computational functionality.
4. Passing automated tests.
5. Verified statistical calculations.
6. Appropriate validation.
7. Defined limitations and execution constraints.

The platform should expose the actual capability state rather than presenting all catalogue entries as executable.

---

# PART XIII: TIMANSTAT ARCHITECTURAL PRINCIPLES

# 39. STATISTICAL KNOWLEDGE AND EXECUTION ARCHITECTURE

TimanStat should use a layered architecture.

## 39.1 Layer 1: Statistical knowledge base

Contains:

- Statistical concepts.
- Knowledge areas.
- Methods.
- Models.
- Study designs.
- Diagnostics.
- Algorithms.
- Measures.
- Visualisations.
- Methodological relationships.

This layer defines what TimanStat knows.

## 39.2 Layer 2: Research-objective understanding

Interprets the user's research objective and identifies:

- Research purpose.
- Research question.
- Population of interest.
- Outcome of interest.
- Explanatory variables.
- Study design.
- Desired estimand.
- Required analytical output.

This layer translates natural-language objectives into structured analytical requirements.

## 39.3 Layer 3: Data understanding and profiling

Examines:

- Dataset structure.
- Variable types.
- Measurement scales.
- Missingness.
- Duplicates.
- Outliers.
- Data validity.
- Data consistency.
- Sampling structure.
- Repeated observations.
- Clustering.
- Temporal and spatial structure.

This layer establishes whether the supplied data can support the requested analysis.

## 39.4 Layer 4: Method selection

Uses the research objective, data structure, variables, study design, sampling design and assumptions to recommend suitable analytical methods.

It should:

- Identify candidate methods.
- Explain why each candidate is relevant.
- Identify unsuitable methods.
- Explain necessary assumptions.
- Identify alternatives.
- Ask clarifying questions where information is insufficient.
- Distinguish recommended methods from executable methods.

## 39.5 Layer 5: Statistical model specification

Converts the selected method into a formal analytical specification.

A general statistical model specification should accommodate:

- Analysis type.
- Outcome variable.
- Predictor variables.
- Factors.
- Covariates.
- Interaction terms.
- Study design.
- Sampling structure.
- Hypotheses.
- Estimand.
- Assumptions.
- Execution settings.

The specification must use controlled identifiers and structured parameters rather than arbitrary executable code.

## 39.6 Layer 6: Validation and diagnostics

Checks:

- Variable compatibility.
- Data sufficiency.
- Model specification.
- Study-design compatibility.
- Sampling-design compatibility.
- Assumptions.
- Missing-data implications.
- Numerical feasibility.
- Execution constraints.

Where an assumption is violated, TimanStat should explain the consequence and consider appropriate alternatives rather than silently proceeding.

## 39.7 Layer 7: Statistical computation

Executes the validated analytical specification through approved statistical functions and computational algorithms.

The computational engine should:

- Use validated functions.
- Apply appropriate numerical procedures.
- Record analytical provenance.
- Handle errors explicitly.
- Return structured outputs.
- Avoid arbitrary code execution.
- Preserve reproducibility.

## 39.8 Layer 8: Results verification

Checks:

- Numerical consistency.
- Expected result structure.
- Degrees of freedom.
- Sample sizes.
- Missing observations.
- Convergence.
- Numerical precision.
- Reference or benchmark agreement, where available.

## 39.9 Layer 9: Interpretation and communication

Produces:

- Statistical interpretation.
- Practical interpretation.
- Effect sizes.
- Uncertainty estimates.
- Limitations.
- Diagnostic findings.
- Visualisations.
- Reports.
- Reproducibility information.

The interpretation must be consistent with the method, estimand, assumptions and evidence actually produced.

---

# 40. METHOD SELECTION PRINCIPLES

The method-selection engine must not choose an analysis based only on the name of a statistical test or the measurement scale of one variable.

It must consider the full analytical context.

## 40.1 Research objective

What is the user trying to establish?

Examples:

- Describe a population.
- Compare groups.
- Determine an association.
- Estimate a population parameter.
- Predict an outcome.
- Evaluate a treatment effect.
- Examine change over time.
- Analyse time to an event.

## 40.2 Outcome and explanatory variables

The system must identify:

- Outcome variable.
- Predictor variables.
- Grouping variables.
- Factors.
- Covariates.
- Potential confounders.
- Time variables.
- Cluster identifiers.
- Sampling weights.

## 40.3 Measurement scales

- Nominal.
- Ordinal.
- Interval.
- Ratio.

The system must distinguish the measurement scale from the statistical distribution and data structure.

## 40.4 Data structure

- Independent observations.
- Paired observations.
- Repeated observations.
- Clustered observations.
- Nested observations.
- Longitudinal observations.
- Time-series observations.
- Spatial observations.
- Survival data.
- Complex survey data.

## 40.5 Study design

- Experimental.
- Observational.
- Cross-sectional.
- Cohort.
- Case-control.
- Repeated-measures.
- Randomised controlled trial.
- Cluster-randomised trial.
- Quasi-experimental.
- Other applicable designs.

## 40.6 Sampling design

- Simple random sampling.
- Stratified sampling.
- Cluster sampling.
- Multistage sampling.
- Non-probability sampling.
- Complex survey sampling.

## 40.7 Assumptions and diagnostics

The method selector must assess whether the required assumptions are plausible and whether they can be evaluated from the available data.

## 40.8 Estimand

The system must identify the quantity the user wants to estimate or test.

Examples:

- Population mean.
- Difference between population means.
- Population proportion.
- Difference between proportions.
- Correlation.
- Regression coefficient.
- Risk ratio.
- Odds ratio.
- Average treatment effect.
- Hazard ratio.
- Predicted probability.

## 40.9 Selection output

The method-selection process should produce:

1. Primary recommended method.
2. Alternative methods, where appropriate.
3. Rationale.
4. Required variables.
5. Assumptions.
6. Data suitability assessment.
7. Diagnostics.
8. Expected outputs.
9. Limitations.
10. Implementation availability.

---

# 41. GENERAL STATISTICAL MODEL CONTRACT

TimanStat should maintain a common statistical model specification that can support different analytical methods.

The specification should include:

- `analysis_type`
- `entity_id`
- `outcome_variable`
- `predictor_variables`
- `factors`
- `covariates`
- `interaction_terms`
- `design`
- `sampling_design`
- `data_structure`
- `estimand`
- `hypotheses`
- `assumptions`
- `execution_settings`

The model contract must be extensible. Different statistical procedures will require additional method-specific parameters.

A common contract should not force unrelated methods into identical mathematical specifications.

The system must distinguish:

- General model fields.
- Method-specific fields.
- Required fields.
- Optional fields.
- Validated values.
- Unsupported values.

---

# 42. STATISTICAL ENGINE DESIGN PRINCIPLES

## 42.1 Shared statistical infrastructure

The engine should provide common services for:

- Input validation.
- Variable-role validation.
- Model specification.
- Assumption assessment.
- Result structures.
- Effect-size calculation.
- Confidence-interval calculation.
- Diagnostic reporting.
- Numerical verification.
- Provenance.
- Error handling.

## 42.2 Method-specific computation

Individual method implementations should contain the mathematical calculations and procedures specific to that method.

Examples:

- Independent-samples t-test.
- One-way ANOVA.
- Chi-square test.
- Linear regression.
- Logistic regression.
- Kaplan–Meier estimation.

## 42.3 Avoiding duplicated infrastructure

The system should not build separate, unrelated inferential engines for every statistical test.

Methods that share statistical concepts should reuse common infrastructure while retaining their own mathematical procedures.

## 42.4 Execution safety

- No arbitrary code execution from user questions.
- Controlled method identifiers.
- Controlled model parameters.
- Input validation.
- Numerical safeguards.
- Explicit error handling.
- Reproducibility.
- Traceable analytical provenance.

---

# 43. STATISTICAL RESULT AND PROVENANCE FRAMEWORK

Every analysis should return a structured result containing the information relevant to its method.

## 43.1 Core result fields

- Analysis title.
- Method identifier.
- Method name.
- Execution status.
- Research objective.
- Dataset reference.
- Analytical sample size.
- Variables used.
- Model specification.
- Estimates.
- Test statistics.
- Degrees of freedom, where applicable.
- P-values, where applicable.
- Confidence or credible intervals.
- Effect sizes.
- Diagnostics.
- Assumptions.
- Findings.
- Limitations.
- Interpretation.
- Metadata.

## 43.2 Provenance

The platform should retain:

- Dataset identity.
- Data version or fingerprint.
- Variables used.
- Method identifier and version.
- Model specification.
- Execution parameters.
- Software dependencies.
- Execution timestamp.
- Random seed, where applicable.
- Diagnostic results.
- Verification results.

## 43.3 Error and warning handling

The system must distinguish:

- Invalid input.
- Missing required variables.
- Incompatible data.
- Violated assumptions.
- Insufficient sample size.
- Numerical failure.
- Non-convergence.
- Unsupported method.
- Unavailable implementation.
- Successful execution with limitations.

Warnings must not be silently converted into successful results.

---

# 44. FUTURE EXTENSIBILITY

The catalogue must allow additional statistical methods and disciplines to be introduced without restructuring the core architecture.

Potential extensions include:

- Advanced functional data analysis.
- Compositional data analysis.
- Extreme-value statistics.
- Directional statistics.
- Mathematical statistics.
- Information theory.
- Network statistics.
- Spatial-temporal modelling.
- Causal machine learning.
- Advanced statistical decision theory.
- Statistical genetics.
- Environmental statistics.
- Ecological statistics.
- Bayesian non-parametric methods.
- Advanced multivariate modelling.
- Statistical privacy and disclosure control.
- Differential privacy.
- Federated statistical analysis.

New entities must follow the same classification, metadata, relationship and verification principles.

---

# 45. GOVERNANCE AND MAINTENANCE OF THE CATALOGUE

## 45.1 Catalogue governance

The catalogue should be maintained as a controlled statistical knowledge resource.

Changes should be documented and versioned.

## 45.2 Adding a new method

A new method should be registered only after identifying:

- Its canonical name.
- Its entity type.
- Its statistical purpose.
- Its knowledge area.
- Its method family.
- Its research objectives.
- Its data requirements.
- Its assumptions.
- Its outputs.
- Its relationships to existing entities.
- Its authoritative methodological references.

## 45.3 Updating existing methods

Updates should preserve the canonical entity identifier unless there is a compelling reason to create a new entity.

Changes to definitions, assumptions, selection rules or computational requirements should be versioned.

## 45.4 Avoiding duplication

Before creating a new record, the catalogue manager should check for:

- Existing canonical records.
- Alternative names.
- Closely related procedures.
- Special cases of existing methods.
- Methods that differ only by an inferential paradigm.

## 45.5 Methodological references

Each method should eventually be supported by authoritative references, including recognised statistical textbooks, peer-reviewed methodological literature and appropriate technical documentation.

References should be associated with the specific entity they support.

---

# 46. FINAL ARCHITECTURAL PRINCIPLES

1. The catalogue must be comprehensive, structured and extensible.
2. Every statistical entity must have a unique canonical identifier.
3. Methods, models, designs, diagnostics, algorithms, measures, visualisations and principles must be represented as distinct entity types.
4. Statistical purpose must be distinguished from knowledge area.
5. Inference paradigm must be distinguished from method family.
6. Bayesian statistics must remain a first-class knowledge area and inference paradigm.
7. Experimental design must remain a first-class study-design domain.
8. Descriptive and inferential analysis must remain central analytical purposes.
9. Probability theory and mathematical statistics must be represented as foundational knowledge areas.
10. A method may have multiple domain relationships without having duplicate canonical records.
11. Every method must have explicit data and variable requirements.
12. Method selection must consider the research objective, estimand, data structure, variable types, sampling design, study design and assumptions.
13. Diagnostics must be distinguished from primary analytical methods.
14. Computational algorithms must be distinguished from statistical models.
15. Effect sizes and uncertainty measures must be methodologically appropriate.
16. Statistical calculations must be separated from method selection and reporting.
17. Shared statistical infrastructure should be reused across related methods.
18. Method-specific mathematical procedures must remain explicit and independently verifiable.
19. Statistical computations must be traceable and reproducible.
20. No method should be represented as operational without appropriate implementation, testing, verification and validation.
21. Unsupported methods must not be silently substituted with superficially similar procedures.
22. The platform must communicate uncertainty, assumptions and limitations honestly.
23. The catalogue must accommodate future statistical disciplines without redesigning its core architecture.

---

# 47. CONCLUSION

The TimanStat Statistical Methods Catalogue is the foundation of the platform's statistical knowledge architecture.

Its purpose is not simply to provide a list of statistical tests. It is to establish a structured representation of statistical knowledge that allows TimanStat to understand research objectives, recognise appropriate analytical approaches, reason about data suitability, specify statistical models, coordinate validated computations and communicate defensible results.

The catalogue therefore serves three connected purposes:

1. **Statistical knowledge:** defining what TimanStat should know.
2. **Analytical intelligence:** defining how TimanStat should reason about research questions and select appropriate methods.
3. **Statistical execution:** defining how selected methods will eventually be specified, computed, verified and reported.

The complete catalogue should be registered before implementation is prioritised. Implementation can then proceed incrementally, beginning with a carefully selected set of methods while preserving the broader statistical architecture.

**End of TimanStat Statistical Methods Catalogue, Version 2.1.**
