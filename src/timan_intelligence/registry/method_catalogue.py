"""Curated statistical method catalogue built on the shared registry.

This catalogue describes method requirements and lifecycle status. It does
not implement statistical calculations or independently determine whether
a method is suitable for a particular dataset.
"""

from __future__ import annotations

import copy
from collections import Counter
from typing import Any

from timan_intelligence.registry.identifiers import validate_entity_id
from timan_intelligence.registry.identity import RegistryIdentityIndex
from timan_intelligence.registry.method import MethodEntity
from timan_intelligence.registry.method_repository import MethodRepository


CATALOGUE_VERSION = "1.0.0"

IMPLEMENTED_METHODS = frozenset(
    {
        "method.descriptive.numeric.summary",
        "method.inference.confidence_interval.mean",
        "method.inference.comparison.t_test.one_sample",
        "method.inference.comparison.binomial.one_sample",
        "method.inference.comparison.proportions.independent",
        "method.inference.confidence_interval.proportions.independent",
        "method.inference.comparison.t_test.paired",
        "method.inference.association.chi_square.independence",
        "method.inference.association.fisher_exact",
        "method.inference.confidence_interval.proportion",
        "method.inference.confidence_interval.mean_difference.welch",
        "method.inference.confidence_interval.mean_difference.paired",
        "method.inference.comparison.t_test.independent.welch",
        "method.inference.comparison.anova.one_way",
        "method.inference.comparison.mann_whitney",
        "method.inference.comparison.kruskal_wallis",
        "method.inference.comparison.posthoc.dunn_holm",
        "method.inference.comparison.wilcoxon_signed_rank",
        "method.inference.comparison.friedman",
        "method.inference.comparison.posthoc.friedman_wilcoxon_holm",
        "method.inference.comparison.anova.repeated_measures",\n        "method.inference.regression.linear_mixed_effects",
    }
)


def _method(
    *,
    entity_id: str,
    name: str,
    description: str,
    family: str,
    purpose: str,
    priority: str,
    outcome_types: list[str],
    data_requirements: list[str],
    assumptions: list[str],
    outputs: list[str],
    use_cases: list[str],
    required_roles: list[str] | None = None,
    predictor_types: list[str] | None = None,
    study_designs: list[str] | None = None,
    aliases: list[str] | None = None,
    limitations: list[str] | None = None,
    implementation_status: str = "planned",
    verification_status: str = "not_tested",
    execution_eligibility: str = "not_assessed",
    validation_requirements: list[str] | None = None,
) -> MethodEntity:
    """Construct a method record using the shared registry contract."""
    implemented = implementation_status == "implemented"
    return MethodEntity(
        entity_id=entity_id,
        name=name,
        description=description,
        knowledge_areas=[family],
        statistical_purposes=[purpose],
        record_maturity="reviewed" if implemented else "catalogued",
        implementation_status=implementation_status,
        verification_status=verification_status,
        execution_eligibility=execution_eligibility,
        aliases=list(aliases or []),
        application_domains=[
            "general_research",
            "public_health",
            "development",
            "business",
            "education",
            "agriculture",
        ],
        tags=[family, purpose, priority.lower()],
        method_families=[family],
        use_cases=list(use_cases),
        data_requirements=list(data_requirements),
        statistical_specification={
            "method_family": family,
            "statistical_purpose": purpose,
            "release_priority": priority,
            "outcome_types": list(outcome_types),
            "predictor_types": list(predictor_types or []),
            "required_variable_roles": list(required_roles or []),
            "compatible_study_designs": list(study_designs or []),
            "sampling_design_aware": False,
        },
        assumptions=list(assumptions),
        outputs=list(outputs),
        computational_requirements=[
            "A valid dataset with the required variables.",
            "Method-specific sample-size and data-type checks.",
        ],
        validation_requirements=list(
            validation_requirements
            or [
                "Validate variable roles and measurement scales.",
                "Assess missing data and invalid values.",
                "Check method-specific assumptions before interpretation.",
                "Record exclusions, warnings and limitations.",
            ]
        ),
        limitations=list(limitations or []),
        provenance={
            "catalogue": "TimanStat Statistical Methods Catalogue",
            "catalogue_version": CATALOGUE_VERSION,
            "record_source": "curated_initial_registry",
        },
        metadata={
            "release_priority": priority,
            "method_family": family,
            "catalogue_version": CATALOGUE_VERSION,
            "calculation_implemented": implemented,
        },
    )


def _build_catalogue() -> tuple[MethodEntity, ...]:
    """Return the curated first-release catalogue.

    Only methods with an existing, tested execution function are marked
    implemented. Planned records are discoverable but must not be executed.
    """
    methods = [
        _method(
            entity_id="method.descriptive.numeric.summary",
            name="Descriptive statistics",
            description="Summarises the centre, spread and range of a numeric variable.",
            family="descriptive_statistics",
            purpose="description",
            priority="P1",
            outcome_types=["numeric"],
            required_roles=["analysis_variable"],
            data_requirements=["At least one numeric variable."],
            assumptions=["The variable's numeric values represent a meaningful quantity."],
            outputs=["Valid observation count", "Mean", "Median", "Sample standard deviation", "Minimum", "Maximum", "Quartiles"],
            use_cases=["Describe a numeric variable", "Summarise continuous measurements"],
            aliases=["Numeric summary", "Summary statistics"],
            implementation_status="implemented",
            verification_status="unit_tested",
            execution_eligibility="eligible",
            limitations=["Descriptive summaries alone do not support population inference or causal conclusions."],
        ),
        _method(
            entity_id="method.descriptive.categorical.frequency",
            name="Frequency distribution",
            description="Counts category occurrences and calculates proportions and percentages.",
            family="descriptive_statistics",
            purpose="description",
            priority="P1",
            outcome_types=["categorical", "binary", "ordinal"],
            required_roles=["analysis_variable"],
            data_requirements=["One categorical, binary or ordinal variable."],
            assumptions=["Category labels and missing-value codes have been reviewed."],
            outputs=["Category counts", "Valid percentages", "Cumulative percentages", "Missing count"],
            use_cases=["Describe categorical responses", "Summarise survey questions", "Profile population characteristics"],
            aliases=["Frequencies", "Frequencies and proportions", "Frequency table", "Counts and percentages"],
        ),
        _method(
            entity_id="method.descriptive.categorical.cross_tabulation",
            name="Cross-tabulation",
            description="Summarises the joint distribution of two or more categorical variables.",
            family="descriptive_statistics",
            purpose="description",
            priority="P1",
            outcome_types=["categorical", "binary", "ordinal"],
            required_roles=["row_variable", "column_variable"],
            data_requirements=["At least two categorical variables."],
            assumptions=["Category definitions are consistent.", "The denominator for row or column percentages is explicit."],
            outputs=["Observed cell counts", "Row percentages", "Column percentages", "Total percentages"],
            use_cases=["Compare response patterns across groups", "Disaggregate survey indicators"],
            aliases=["Contingency table", "Crosstab"],
        ),
        _method(
            entity_id="method.inference.comparison.t_test.one_sample",
            name="One-sample Student's t-test",
            description="Tests whether a numeric population mean differs from a specified reference value using a one-sample Student-t statistic.",
            family="estimation",
            purpose="inference",
            priority="P1",
            outcome_types=["numeric"],
            required_roles=["analysis_variable"],
            data_requirements=["One numeric outcome and a finite, prespecified reference value.", "At least two finite observations."],
            assumptions=["Observations are independent.", "The outcome distribution is compatible with the one-sample t model, particularly for small samples."],
            outputs=["Sample mean", "Reference value", "Mean difference", "t statistic", "Degrees of freedom", "p-value", "95% confidence interval"],
            use_cases=["Test an average against a programme target or benchmark", "Compare a sample mean with a policy or service standard"],
            aliases=["One sample t test", "One-sample t-test", "Single-sample Student t-test"],
            implementation_status="implemented",
            verification_status="unit_tested",
            execution_eligibility="conditional",
            limitations=[
                "Assumes independent observations and does not adjust for complex survey designs.",
                "The current test reports a two-sided or one-sided p-value and a two-sided 95% confidence interval.",
            ],
        ),
        _method(
            entity_id="method.inference.confidence_interval.proportions.independent",
            name="Confidence interval for difference in two proportions",
            description="Estimates group 1 minus group 2 for two independent binary proportions using a Newcombe-Wilson confidence interval.",
            family="estimation", purpose="inference", priority="P1",
            outcome_types=["binary"], required_roles=["binary_outcome", "grouping_variable"],
            data_requirements=["A numeric binary outcome coded 1 for event and 0 for non-event.", "A grouping variable with exactly two independent groups."],
            assumptions=["Independent observations within and between groups."],
            outputs=["Group event counts and proportions", "Difference in proportions (group 1 minus group 2)", "Newcombe-Wilson confidence interval"],
            use_cases=["Quantify programme coverage differences between locations", "Estimate uptake or completion gaps between two groups", "Report uncertainty around a binary outcome difference"],
            aliases=["Two-proportion confidence interval", "Independent proportions difference interval", "Newcombe confidence interval for two proportions"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Not adjusted for complex survey sampling, clustering, stratification or unequal weights.", "Requires independent groups; do not use for matched or repeated observations."],
        ),
        _method(
            entity_id="method.inference.comparison.proportions.independent",
            name="Two-independent-proportions comparison",
            description="Compares a binary event proportion between two independent groups using a pooled score test and Newcombe-Wilson confidence interval.",
            family="group_comparison", purpose="inference", priority="P1",
            outcome_types=["binary"], required_roles=["binary_outcome", "grouping_variable"],
            data_requirements=["A numeric binary outcome coded 1 for event and 0 for non-event.", "A grouping variable with exactly two independent groups."],
            assumptions=["Independent observations within and between groups.", "A common event probability within each group."],
            outputs=["Group event counts and proportions", "Difference in proportions (group 1 minus group 2)", "Pooled score z statistic and p-value", "Newcombe-Wilson confidence interval"],
            use_cases=["Compare programme coverage between locations", "Compare uptake or completion between intervention groups", "Compare binary outcomes between two independent populations"],
            aliases=["Two-proportion z test", "Independent proportions test", "Difference between two proportions"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Not adjusted for complex survey sampling, clustering, stratification or unequal weights.", "Requires independent groups; do not use for matched or repeated observations."],
        ),
        _method(
            entity_id="method.inference.comparison.binomial.one_sample",
            name="Exact one-sample binomial test",
            description="Tests whether a binary population event probability differs from a specified reference proportion using an exact binomial distribution.",
            family="hypothesis_test", purpose="inference", priority="P1",
            outcome_types=["binary"], required_roles=["binary_outcome"],
            data_requirements=["A numeric binary outcome coded 1 for event and 0 for non-event.", "A reference population proportion between 0 and 1."],
            assumptions=["Independent Bernoulli observations.", "A common event probability across observations."],
            outputs=["Observed proportion", "Exact binomial p-value", "Exact Clopper-Pearson confidence interval"],
            use_cases=["Test programme coverage against a target", "Test prevalence against a benchmark"],
            aliases=["Exact binomial test", "One-sample exact proportion test"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Not adjusted for complex survey sampling, clustering or unequal weights.", "Assumes independent observations with a common event probability."],
        ),
        _method(
            entity_id="method.inference.confidence_interval.mean",
            name="Confidence interval for a mean",
            description="Estimates a population mean with a confidence interval under a stated sampling and modelling framework.",
            family="estimation",
            purpose="inference",
            priority="P1",
            outcome_types=["numeric"],
            required_roles=["analysis_variable"],
            data_requirements=["A numeric outcome and a defined sampling or modelling framework."],
            assumptions=["Observations and sampling structure are correctly represented.", "The selected interval procedure is appropriate for the data and sample size."],
            outputs=["Sample mean", "Standard error", "Confidence level", "Lower confidence limit", "Upper confidence limit"],
            use_cases=["Estimate an average outcome", "Quantify uncertainty around a sample mean"],
            aliases=["One-sample mean confidence interval", "Student-t interval for a mean"],
            implementation_status="implemented",
            verification_status="unit_tested",
            execution_eligibility="conditional",
            limitations=[
                "The current implementation assumes independent, identically distributed observations.",
                "It is not design-adjusted for complex survey samples, clustering, stratification or sampling weights.",
            ],
        ),
        _method(
            entity_id="method.inference.confidence_interval.proportion",
            name="Confidence interval for a proportion",
            description="Estimates a population proportion with an interval using an appropriate binomial or survey-based procedure.",
            family="estimation",
            purpose="inference",
            priority="P1",
            outcome_types=["binary", "categorical"],
            required_roles=["binary_outcome"],
            data_requirements=["A clearly defined numerator and denominator."],
            assumptions=["The outcome definition is valid.", "The sampling design is reflected in the selected interval procedure."],
            outputs=["Estimated proportion", "Standard error", "Confidence level", "Lower confidence limit", "Upper confidence limit"],
            use_cases=["Estimate prevalence", "Estimate coverage", "Report programme indicator proportions"],
            aliases=["Wilson proportion confidence interval", "Binary proportion confidence interval"],
            implementation_status="implemented",
            verification_status="unit_tested",
            execution_eligibility="conditional",
            limitations=[
                "The current implementation assumes independent Bernoulli observations.",
                "It is not design-adjusted for complex survey samples, clustering, stratification or sampling weights.",
            ],
        ),
        _method(
            entity_id="method.inference.confidence_interval.mean_difference.paired",
            name="Paired mean-change confidence interval",
            description="Estimates the mean after-minus-before change in correctly matched measurements using a paired Student-t interval.",
            family="estimation",
            purpose="inference",
            priority="P1",
            outcome_types=["numeric"],
            required_roles=["paired_measurement_before", "paired_measurement_after"],
            study_designs=["paired", "repeated_measure"],
            data_requirements=["Two numeric before-and-after measurements in separate columns.", "Each row represents one correctly matched pair.", "At least two complete finite pairs."],
            assumptions=["Pairs are correctly matched.", "Pair-level differences are independent across rows.", "The distribution of paired differences is assessed."],
            outputs=["Complete pair count", "Mean before", "Mean after", "Mean change (after minus before)", "Standard error", "Degrees of freedom", "Confidence interval"],
            use_cases=["Estimate pre/post programme change", "Quantify within-participant change", "Analyse matched repeated measurements"],
            aliases=["Paired mean difference interval", "Before-after mean change confidence interval"],
            implementation_status="implemented",
            verification_status="unit_tested",
            execution_eligibility="conditional",
            limitations=[
                "Each row must represent one correctly matched pair; unmatched observations are excluded.",
                "The interval is not adjusted for complex survey sampling or clustering.",
            ],
        ),
        _method(
            entity_id="method.inference.confidence_interval.mean_difference.welch",
            name="Welch confidence interval for a mean difference",
            description="Estimates the difference between two independent group means using a Welch-Satterthwaite confidence interval.",
            family="estimation",
            purpose="inference",
            priority="P1",
            outcome_types=["numeric"],
            required_roles=["numeric_outcome", "two_group_factor"],
            data_requirements=["A numeric outcome.", "A grouping variable with exactly two observed groups.", "At least two finite observations in each group."],
            assumptions=["The groups are independent.", "Observations are independent within groups.", "Welch-Satterthwaite approximation is appropriate."],
            outputs=["Group means", "Mean difference", "Standard error", "Welch degrees of freedom", "Confidence interval"],
            use_cases=["Quantify an intervention-versus-comparison mean difference", "Estimate uncertainty around a difference between two independent means"],
            aliases=["Welch mean difference confidence interval", "Independent means difference interval"],
            implementation_status="implemented",
            verification_status="unit_tested",
            execution_eligibility="conditional",
            limitations=[
                "Assumes independent observations and does not assume equal group variances.",
                "Not adjusted for complex survey designs, clustering, stratification or sampling weights.",
            ],
        ),
        _method(
            entity_id="method.inference.comparison.t_test.independent.welch",
            name="Welch's independent-samples t-test",
            description="Compares the means of a numeric outcome between two independent groups without assuming equal population variances.",
            family="group_comparison",
            purpose="inference",
            priority="P1",
            outcome_types=["numeric"],
            required_roles=["numeric_outcome", "two_group_factor"],
            data_requirements=["A numeric outcome.", "A grouping variable with exactly two observed groups.", "Independent observations."],
            assumptions=["The two groups are independent.", "Observations are independent within groups.", "The outcome is numeric; severe influential observations and distribution shape require review."],
            outputs=["Group sample sizes", "Group means", "Mean difference", "Welch t-statistic", "Degrees of freedom", "P-value", "Confidence interval"],
            use_cases=["Compare a numeric outcome between two independent groups", "Compare intervention and comparison groups when design permits"],
            aliases=["Welch t-test", "Unequal-variance t-test", "Independent-samples t-test"],
            implementation_status="implemented",
            verification_status="unit_tested",
            execution_eligibility="conditional",
            limitations=["The existing execution function must be checked for sampling-design compatibility before use on clustered or weighted survey data."],
        ),
        _method(
            entity_id="method.inference.comparison.anova.one_way",
            name="One-way ANOVA",
            description="Tests whether the means of a numeric outcome differ across independent groups.",
            family="group_comparison",
            purpose="inference",
            priority="P1",
            outcome_types=["numeric"],
            required_roles=["numeric_outcome", "grouping_factor"],
            data_requirements=["A numeric outcome.", "A categorical grouping variable with at least two groups.", "Independent observations."],
            assumptions=["Independent observations.", "Residual distribution is reasonably compatible with the model.", "Variance assumptions are assessed."],
            outputs=["Group count", "Observation count", "F-statistic", "Degrees of freedom", "P-value"],
            use_cases=["Compare mean outcomes across multiple independent groups", "Compare outcomes across programme arms"],
            implementation_status="implemented",
            verification_status="unit_tested",
            execution_eligibility="conditional",
            limitations=["A significant omnibus result does not identify which groups differ.", "The current implementation does not provide post-hoc comparisons or design-based survey inference."],
        ),
        _method(
            entity_id="method.inference.comparison.t_test.paired",
            name="Paired-samples t-test",
            description="Tests the mean within-pair difference for two related measurements.",
            family="group_comparison",
            purpose="inference",
            priority="P1",
            outcome_types=["numeric"],
            required_roles=["paired_measurement_before", "paired_measurement_after", "pair_identifier"],
            study_designs=["paired", "repeated_measure"],
            data_requirements=["Two numeric measurements linked to the same unit or matched pair."],
            assumptions=["Pairs are correctly matched.", "Pair-level differences are independent.", "The distribution of differences is assessed."],
            outputs=["Pair count", "Mean difference (after minus before)", "Standard error", "t-statistic", "Degrees of freedom", "P-value", "Confidence interval"],
            use_cases=["Before-and-after programme evaluation", "Repeated measurement of the same participants"],
            aliases=["Paired t-test", "Matched-pairs t-test", "Dependent-samples t-test"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Requires correctly matched pairs and independent pair-level differences.", "Not adjusted for complex survey sampling or clustering.", "The confidence interval is two-sided even when a one-sided alternative is selected."],
        ),


        _method(
            entity_id="method.inference.comparison.posthoc.friedman_wilcoxon_holm",
            name="Pairwise Wilcoxon post-hoc test with Holm adjustment",
            description="Identifies which repeated measurements differ using paired Wilcoxon signed-rank tests with Holm family-wise error adjustment.",
            family="group_comparison", purpose="inference", priority="P1", outcome_types=["ordinal", "numeric"],
            required_roles=["repeated_measurement_variables", "unit_identifier"],
            study_designs=["repeated_measure", "repeated_measures", "longitudinal"],
            data_requirements=["At least three repeated measurement columns, one row per correctly matched unit; preferably follow a significant Friedman omnibus test."],
            assumptions=["Measurements are matched within each unit.", "Different units are independent.", "Paired differences support signed-rank inference."],
            outputs=["Pairwise Wilcoxon statistics", "Raw p-values", "Holm-adjusted p-values", "Rank-biserial correlations"],
            use_cases=["Identify which programme time points differ after a Friedman test", "Compare related conditions with family-wise error control"],
            aliases=["Friedman post-hoc Wilcoxon Holm", "Pairwise Wilcoxon repeated measures Holm"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Use as follow-up to an omnibus Friedman test.", "Complete-case analysis across all selected measures.", "Not adjusted for complex survey sampling."]),
        _method(
            entity_id="method.inference.comparison.anova.repeated_measures",
            name="One-way repeated-measures ANOVA",
            description="Compares means across three or more related conditions/time points, assesses sphericity, applies Greenhouse-Geisser and Huynh-Feldt corrections, and provides Holm-adjusted paired follow-ups.",
            family="group_comparison", purpose="inference", priority="P1", outcome_types=["numeric"],
            required_roles=["repeated_measurement_variables", "unit_identifier"],
            study_designs=["repeated_measure", "repeated_measures", "longitudinal"],
            data_requirements=["At least three numeric repeated-measurement columns, one row per matched unit, with complete observations for selected measures."],
            assumptions=["Different units are independent.", "Within-subject contrasts/residuals are approximately multivariate normal.", "Sphericity is assessed and corrected degrees of freedom are used when appropriate."],
            outputs=["Repeated-measures F statistic", "Mauchly sphericity test", "Greenhouse-Geisser and Huynh-Feldt corrections", "Partial eta-squared", "Holm-adjusted paired comparisons"],
            use_cases=["Compare mean outcomes across baseline, midline and endline", "Compare three or more repeated treatment conditions"],
            aliases=["Repeated measures ANOVA", "Within-subjects one-way ANOVA"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Complete-case analysis is used.", "Pairwise confidence intervals are unadjusted while p-values are Holm-adjusted.", "Not adjusted for complex survey sampling.", "Not a substitute for mixed-effects models with complex missingness or hierarchical structures."]),
        _method(
            entity_id="method.inference.comparison.friedman",
            name="Friedman test",
            description="Compares three or more related conditions or time points using within-unit ranks.",
            family="group_comparison", purpose="inference", priority="P1",
            outcome_types=["ordinal", "numeric"],
            required_roles=["repeated_measurement_variables", "unit_identifier"],
            study_designs=["repeated_measure", "repeated_measures", "longitudinal"],
            data_requirements=["At least three repeated measurement columns, with one row per unit and measurements aligned across columns."],
            assumptions=["Repeated measurements are correctly matched within each unit.", "Different units are independent.", "The outcome is at least ordinal."],
            outputs=["Friedman chi-square statistic", "Degrees of freedom", "P-value", "Kendall's W", "Mean within-unit ranks"],
            use_cases=["Compare baseline, midline and endline measurements", "Compare three or more related treatment or programme conditions"],
            aliases=["Friedman rank test", "Friedman two-way analysis of variance by ranks"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Omnibus test does not identify which pairs differ; use an appropriate paired post-hoc procedure with multiplicity adjustment.", "Not adjusted for complex survey sampling or clustering.", "Complete-case analysis is used."],
        ),
        _method(
            entity_id="method.inference.comparison.wilcoxon_signed_rank",
            name="Wilcoxon signed-rank test",
            description="Compares two related measurements using signed ranks of within-pair differences.",
            family="group_comparison", purpose="inference", priority="P1",
            outcome_types=["ordinal", "numeric"],
            required_roles=["paired_measurement_before", "paired_measurement_after", "pair_identifier"],
            study_designs=["paired", "repeated_measure"],
            data_requirements=["Two ordered measurements correctly matched within the same unit."],
            assumptions=["Pairs are correctly matched.", "Pair-level differences are independent.", "The distribution of differences is reasonably symmetric for a location-shift interpretation."],
            outputs=["Complete pair count", "Wilcoxon statistic", "P-value", "Positive and negative rank sums", "Matched-pairs rank-biserial correlation"],
            use_cases=["Non-parametric before-and-after programme evaluation", "Paired ordinal or skewed outcome comparison"],
            aliases=["Wilcoxon matched-pairs signed-rank test", "Paired Wilcoxon test", "Signed-rank test"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Requires correctly matched pairs.", "Median-change interpretation requires a suitably symmetric difference distribution.", "Not adjusted for complex survey sampling or clustering."],
        ),
        _method(
            entity_id="method.inference.comparison.mann_whitney",
            name="Mann–Whitney U test",
            description="Compares two independent samples using ranks; interpretation depends on the distributions and estimand.",
            family="group_comparison",
            purpose="inference",
            priority="P2",
            outcome_types=["ordinal", "numeric"],
            required_roles=["outcome", "two_group_factor"],
            data_requirements=["Two independent groups and an ordered outcome."],
            assumptions=["Independent observations.", "Outcome values are at least ordinal.", "Distributional shapes are considered before interpreting a location shift."],
            outputs=["Group sample sizes and medians", "Mann–Whitney U statistic for group 1", "P-value", "Directional rank-biserial correlation", "P-value calculation method"],
            use_cases=["Compare two independent groups using a rank-based procedure", "Compare ordinal or skewed numeric outcomes between independent groups"],
            aliases=["Wilcoxon rank-sum test", "Mann Whitney test", "Rank-sum test"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["It is not automatically a test of medians; a location-shift interpretation requires similarly shaped group distributions.", "The current procedure requires numeric or ordinal values encoded numerically.", "Not adjusted for complex survey sampling, weights, clustering or repeated-measures designs."],
        ),
        _method(
            entity_id="method.inference.comparison.kruskal_wallis",
            name="Kruskal–Wallis test",
            description="Compares rank distributions across three or more independent groups.",
            family="group_comparison",
            purpose="inference",
            priority="P2",
            outcome_types=["ordinal", "numeric"],
            required_roles=["outcome", "grouping_factor"],
            data_requirements=["An ordered outcome and at least two independent groups."],
            assumptions=["Independent observations.", "Outcome values are at least ordinal.", "Group distribution shapes are reviewed."],
            outputs=["H statistic", "P-value", "Group sizes", "Post-hoc analysis requirement"],
            use_cases=["Compare several independent groups using a rank-based procedure"],
            aliases=["Kruskal Wallis", "Kruskal-Wallis H test", "Non-parametric one-way group comparison"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["A significant result does not identify which groups differ; use a justified post-hoc procedure with multiplicity control.", "It is not automatically a test of medians; location-shift interpretation requires similarly shaped distributions.", "Not adjusted for complex survey sampling, weights, clustering, stratification or repeated-measures designs."],
        ),

        _method(
            entity_id="method.inference.comparison.posthoc.dunn_holm",
            name="Dunn post-hoc test with Holm adjustment",
            description="Identifies pairwise rank-distribution differences across independent groups with family-wise error control.",
            family="multiple_comparisons", purpose="inference", priority="P2",
            outcome_types=["ordinal", "numeric"], required_roles=["outcome", "grouping_factor"],
            data_requirements=["At least three independent groups with an ordered outcome."],
            assumptions=["Independent observations.", "The outcome is at least ordinal.", "The pooled rank variance is suitable for the independent-groups design."],
            outputs=["Pairwise mean-rank differences", "Z statistics", "Unadjusted p-values", "Holm-adjusted p-values"],
            use_cases=["Identify which independent groups differ after a rank-based omnibus comparison"],
            aliases=["Dunn test", "Dunn's test", "Dunn pairwise comparisons with Holm correction"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Commonly used after Kruskal–Wallis; it does not replace the omnibus test.", "Not adjusted for complex survey designs or repeated measures.", "Location-shift interpretation requires similarly shaped distributions."],
        ),
        _method(
            entity_id="method.inference.association.chi_square.independence",
            name="Chi-square test of independence",
            description="Assesses evidence of association between two categorical variables using a contingency table.",
            family="categorical_association",
            purpose="inference",
            priority="P1",
            outcome_types=["categorical", "binary", "ordinal"],
            required_roles=["row_variable", "column_variable"],
            data_requirements=["Two categorical variables.", "Observed contingency-table counts."],
            assumptions=["Observations are independent for the ordinary test.", "Expected cell counts are assessed.", "Sampling design is compatible with the ordinary test."],
            outputs=["Contingency table", "Expected counts", "Chi-square statistic", "Degrees of freedom", "P-value", "Association effect size"],
            use_cases=["Test association between categorical variables", "Examine relationships between demographic groups and outcomes"],
            aliases=["Pearson chi-square test", "Chi-square association test"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Requires independent observational units and adequate expected cell counts.", "Not adjusted for complex survey sampling or repeated-measures data.", "Association does not establish causation."],
        ),
        _method(
            entity_id="method.inference.association.fisher_exact",
            name="Fisher's exact test",
            description="Provides an exact test of association for a 2 by 2 contingency table under its sampling assumptions.",
            family="categorical_association",
            purpose="inference",
            priority="P1",
            outcome_types=["categorical", "binary"],
            required_roles=["binary_variable_one", "binary_variable_two"],
            data_requirements=["A 2 by 2 contingency table."],
            assumptions=["Independent observations under the applicable sampling model.", "The table structure and alternative hypothesis are specified."],
            outputs=["Odds ratio", "Exact p-value", "Contingency table"],
            use_cases=["Assess association in a 2 by 2 table, particularly when counts are sparse"],
            aliases=["Fisher exact test", "Exact test for a 2 by 2 table"],
            implementation_status="implemented", verification_status="unit_tested", execution_eligibility="conditional",
            limitations=["Requires a 2 by 2 table and independent observational units.", "Not adjusted for complex survey sampling.", "Odds-ratio confidence interval is not provided by this procedure."],
        ),
        _method(
            entity_id="method.inference.association.correlation.pearson",
            name="Pearson correlation",
            description="Quantifies the strength and direction of a linear association between two numeric variables.",
            family="correlation",
            purpose="association",
            priority="P1",
            outcome_types=["numeric"],
            predictor_types=["numeric"],
            required_roles=["numeric_variable_one", "numeric_variable_two"],
            data_requirements=["Two paired numeric variables."],
            assumptions=["The relationship is approximately linear for linear interpretation.", "Influential outliers are reviewed.", "Inference assumptions are assessed separately from the coefficient."],
            outputs=["Pearson correlation coefficient", "Confidence interval where supported", "P-value where requested", "Sample size"],
            use_cases=["Measure linear association between numeric variables"],
            limitations=["Correlation does not establish causation."],
        ),
        _method(
            entity_id="method.inference.association.correlation.spearman",
            name="Spearman rank correlation",
            description="Measures the strength and direction of a monotonic association using ranks.",
            family="correlation",
            purpose="association",
            priority="P1",
            outcome_types=["ordinal", "numeric"],
            predictor_types=["ordinal", "numeric"],
            required_roles=["ordered_variable_one", "ordered_variable_two"],
            data_requirements=["Two paired variables that can be meaningfully ordered."],
            assumptions=["Observations are paired and independent across units.", "A monotonic relationship is the intended target."],
            outputs=["Spearman rank correlation coefficient", "P-value where requested", "Sample size"],
            use_cases=["Measure monotonic association", "Analyse ordinal-scale relationships"],
            limitations=["Correlation does not establish causation."],
        ),
        _method(
            entity_id="method.inference.regression.linear.multiple",
            name="Multiple linear regression",
            description="Models a numeric outcome using multiple explanatory variables.",
            family="regression",
            purpose="explanation",
            priority="P2",
            outcome_types=["numeric"],
            predictor_types=["numeric", "categorical", "binary"],
            required_roles=["numeric_outcome", "one_or_more_predictors"],
            data_requirements=["A numeric outcome and one or more explanatory variables."],
            assumptions=["Model specification and linearity are assessed.", "Residual variance and dependence are assessed.", "Multicollinearity and influential observations are reviewed."],
            outputs=["Regression coefficients", "Standard errors", "Confidence intervals", "P-values", "Model fit statistics", "Residual diagnostics"],
            use_cases=["Estimate adjusted associations", "Model a numeric outcome"],
            aliases=["Linear regression"],
            limitations=["Associational regression does not establish causal effects without a defensible causal design."],
        ),
        _method(
            entity_id="method.inference.regression.logistic.binary",
            name="Binary logistic regression",
            description="Models the probability or odds of a binary outcome using explanatory variables.",
            family="regression",
            purpose="prediction",
            priority="P2",
            outcome_types=["binary"],
            predictor_types=["numeric", "categorical", "binary"],
            required_roles=["binary_outcome", "one_or_more_predictors"],
            data_requirements=["A binary outcome and one or more explanatory variables."],
            assumptions=["Outcome coding is valid.", "Model specification and predictor relationships are assessed.", "Sample size, separation and influential observations are reviewed."],
            outputs=["Regression coefficients", "Odds ratios", "Confidence intervals", "P-values", "Model diagnostics", "Prediction performance where validated"],
            use_cases=["Model binary outcomes", "Estimate adjusted odds"],
            aliases=["Logistic regression"],
            limitations=["Odds ratios should not be interpreted as risk ratios without justification."],
        ),
        _method(
            entity_id="method.measurement.reliability.cronbach_alpha",
            name="Cronbach's alpha",
            description="Summarises internal consistency for a set of items intended to measure a common construct.",
            family="measurement_reliability",
            purpose="measurement",
            priority="P2",
            outcome_types=["ordinal", "numeric"],
            required_roles=["multi_item_scale"],
            data_requirements=["Multiple items intended to measure a defined construct."],
            assumptions=["Items are coded in consistent directions.", "The scale structure and measurement assumptions are considered."],
            outputs=["Cronbach's alpha", "Item-total statistics", "Item-deletion diagnostics"],
            use_cases=["Assess internal consistency of questionnaire scales", "Review multi-item measurement instruments"],
            limitations=["A high alpha does not establish unidimensionality or validity."],
        ),
        _method(
            entity_id="method.survey.estimation.weighted_proportion",
            name="Weighted survey proportion",
            description="Estimates a population proportion using supplied survey weights and a declared target population.",
            family="survey_estimation",
            purpose="inference",
            priority="P2",
            outcome_types=["binary"],
            required_roles=["binary_outcome", "sampling_weight"],
            data_requirements=["A valid sampling weight and a defined survey target population."],
            assumptions=["Weights are appropriate and documented.", "The sample design and non-response adjustments are understood."],
            outputs=["Weighted proportion", "Unweighted count", "Weighted denominator", "Design-aware uncertainty when supported"],
            use_cases=["Estimate weighted population coverage or prevalence"],
            limitations=["This catalogue entry is planned; ordinary unweighted proportions must not be presented as weighted population estimates."],
        ),
        _method(
            entity_id="method.survey.inference.complex_design",
            name="Complex survey estimation",
            description="Produces design-aware estimates and uncertainty for stratified, clustered or otherwise complex probability samples.",
            family="complex_survey_inference",
            purpose="inference",
            priority="P3",
            outcome_types=["numeric", "binary", "categorical"],
            required_roles=["outcome", "sampling_weight", "stratum_identifier", "cluster_identifier"],
            data_requirements=["Documented sampling weights and applicable strata and cluster identifiers."],
            assumptions=["The sample design is correctly specified.", "Weight construction and finite population corrections are documented where applicable.", "Variance estimation matches the design."],
            outputs=["Design-weighted estimates", "Design-based standard errors", "Confidence intervals", "Design effects", "Effective sample sizes"],
            use_cases=["Analyse stratified and cluster household surveys", "Estimate population indicators from complex samples"],
            limitations=["The full complex-survey execution capability is planned and is not provided by the current ordinary statistical tests."],
        ),
        _method(
            entity_id="method.inference.resampling.bootstrap.confidence_interval",
            name="Bootstrap confidence interval",
            description="Uses resampling to estimate uncertainty for a statistic under a defensible resampling scheme.",
            family="resampling",
            purpose="inference",
            priority="P3",
            outcome_types=["numeric", "ordinal", "categorical"],
            required_roles=["analysis_variables", "statistic_definition"],
            data_requirements=["A defined statistic and a resampling unit consistent with the study design."],
            assumptions=["The resampling scheme reflects the data-generating and sampling structure.", "Monte Carlo error is assessed."],
            outputs=["Bootstrap estimate", "Confidence interval", "Resampling configuration", "Monte Carlo diagnostics"],
            use_cases=["Estimate uncertainty for statistics with difficult analytic intervals"],
            limitations=["Naive row-wise resampling is not valid for every clustered, stratified or dependent dataset."],
        ),
        _method(
            entity_id="method.inference.comparison.posthoc.tukey",
            name="Tukey's honestly significant difference",
            description="Performs pairwise group-mean comparisons following a suitable ANOVA model.",
            family="multiple_comparisons",
            purpose="inference",
            priority="P3",
            outcome_types=["numeric"],
            required_roles=["numeric_outcome", "grouping_factor"],
            data_requirements=["A suitable fitted group-comparison model with at least three groups."],
            assumptions=["The underlying model assumptions are assessed.", "The family of comparisons is defined."],
            outputs=["Pairwise mean differences", "Simultaneous confidence intervals", "Multiplicity-adjusted p-values"],
            use_cases=["Identify which group means differ after an omnibus comparison"],
        ),
        _method(
            entity_id="method.inference.survival.kaplan_meier",
            name="Kaplan–Meier survival analysis",
            description="Estimates a time-to-event survival function while accounting for right-censoring under stated assumptions.",
            family="survival_analysis",
            purpose="description",
            priority="P3",
            outcome_types=["time_to_event"],
            required_roles=["event_time", "event_indicator"],
            data_requirements=["Time-to-event information and an event or censoring indicator."],
            assumptions=["Censoring is appropriately represented.", "The event-time origin and event definition are clear."],
            outputs=["Survival estimates", "Confidence intervals", "Median survival where estimable", "At-risk counts"],
            use_cases=["Describe time to an event", "Analyse programme retention or time-to-event outcomes"],
        ),
        _method(
            entity_id="method.forecasting.time_series.arima",
            name="ARIMA time-series model",
            description="Models temporal dependence in a univariate time series for explanation and forecasting.",
            family="time_series",
            purpose="prediction",
            priority="P3",
            outcome_types=["numeric_time_series"],
            required_roles=["time_index", "numeric_outcome"],
            data_requirements=["A consistently indexed time series with sufficient observations."],
            assumptions=["Time index and frequency are valid.", "Stationarity and differencing requirements are assessed.", "Residual diagnostics and forecast validation are performed."],
            outputs=["Model specification", "Parameter estimates", "Forecasts", "Prediction intervals", "Residual diagnostics"],
            use_cases=["Forecast regularly observed numeric outcomes"],
        ),
    ]
    return tuple(methods)


def create_statistical_method_repository() -> MethodRepository:
    """Build an isolated repository containing the curated method catalogue."""
    identity_index = RegistryIdentityIndex()
    repository = MethodRepository(identity_index)

    for method in _build_catalogue():
        repository.register(method)

    return repository


def get_statistical_methods(
    *,
    implementation_status: str | None = None,
    method_family: str | None = None,
    release_priority: str | None = None,
) -> tuple[MethodEntity, ...]:
    """Return defensive copies of catalogue records matching all filters."""
    methods = create_statistical_method_repository().list_all()

    if implementation_status is not None:
        methods = tuple(
            method for method in methods
            if method.implementation_status == implementation_status
        )

    if method_family is not None:
        methods = tuple(
            method for method in methods
            if method.method_families and method_family in method.method_families
        )

    if release_priority is not None:
        methods = tuple(
            method for method in methods
            if method.metadata.get("release_priority") == release_priority
        )

    return tuple(copy.deepcopy(method) for method in methods)


def get_statistical_method(method_id: str) -> MethodEntity | None:
    """Return one method by canonical identifier, or None when unknown."""
    return create_statistical_method_repository().get(method_id)


def get_statistical_method_summary() -> dict[str, Any]:
    """Return catalogue counts grouped by lifecycle, family and priority."""
    methods = get_statistical_methods()
    statuses = Counter(method.implementation_status for method in methods)
    families = Counter(
        method.method_families[0]
        for method in methods
        if method.method_families
    )
    priorities = Counter(
        str(method.metadata.get("release_priority", "unspecified"))
        for method in methods
    )

    return {
        "catalogue_version": CATALOGUE_VERSION,
        "total_methods": len(methods),
        "implementation_status": dict(sorted(statuses.items())),
        "method_families": dict(sorted(families.items())),
        "release_priorities": dict(sorted(priorities.items())),
    }


def validate_statistical_method_catalogue() -> tuple[str, ...]:
    """Validate canonical IDs and lifecycle consistency across the catalogue."""
    errors: list[str] = []
    methods = _build_catalogue()
    seen: set[str] = set()

    for method in methods:
        try:
            validate_entity_id(method.entity_id, expected_entity_type="method")
        except ValueError as exc:
            errors.append(f"{method.entity_id}: {exc}")

        if method.entity_id in seen:
            errors.append(f"Duplicate method identifier: {method.entity_id}")
        seen.add(method.entity_id)

        if method.implementation_status == "implemented":
            if method.verification_status == "not_tested":
                errors.append(
                    f"{method.entity_id}: implemented method has not been tested."
                )
            if method.execution_eligibility == "not_assessed":
                errors.append(
                    f"{method.entity_id}: implemented method has no execution eligibility assessment."
                )
        elif method.execution_eligibility != "not_assessed":
            errors.append(
                f"{method.entity_id}: non-implemented method must not be executable."
            )

        if method.metadata.get("release_priority") not in {"P1", "P2", "P3"}:
            errors.append(
                f"{method.entity_id}: invalid or missing release priority."
            )

        if not method.description.strip() or not method.assumptions:
            errors.append(
                f"{method.entity_id}: description and assumptions are required."
            )

    return tuple(errors)
