"""Statistical analysis following Dror et al. (ACL 2018).

Implements:
- Bootstrap confidence intervals
- McNemar test (paired binary outcomes)
- Wilcoxon signed-rank test (paired continuous outcomes)
- Benjamini-Hochberg correction for multiple comparisons
- Cohen's d effect size
"""

from typing import Callable, Sequence

import numpy as np
from scipy import stats


def bootstrap_ci(
    data: Sequence[float],
    statistic: Callable[[Sequence[float]], float] = np.mean,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
    random_state: int | None = 42,
) -> tuple[float, float]:
    """Compute bootstrap confidence interval.

    Args:
        data: Sample data.
        statistic: Function to compute statistic (default: mean).
        n_bootstrap: Number of bootstrap samples.
        confidence: Confidence level (default: 0.95).
        random_state: Random seed for reproducibility.

    Returns:
        Tuple of (lower_bound, upper_bound).
    """
    rng = np.random.default_rng(random_state)
    data_array = np.array(data)
    n = len(data_array)

    # Generate bootstrap samples
    bootstrap_stats = []
    for _ in range(n_bootstrap):
        sample = rng.choice(data_array, size=n, replace=True)
        bootstrap_stats.append(statistic(sample))

    # Compute percentile CI
    alpha = 1 - confidence
    lower = np.percentile(bootstrap_stats, 100 * alpha / 2)
    upper = np.percentile(bootstrap_stats, 100 * (1 - alpha / 2))

    return (float(lower), float(upper))


def mcnemar_test(
    correct_a: Sequence[bool],
    correct_b: Sequence[bool],
) -> tuple[float, float]:
    """McNemar's test for paired binary outcomes.

    Tests whether two models have different error rates on paired samples.
    Used when comparing TP/FP/TN/FN outcomes between two systems.

    Args:
        correct_a: Binary outcomes for system A (True = correct).
        correct_b: Binary outcomes for system B (True = correct).

    Returns:
        Tuple of (chi2_statistic, p_value).
    """
    # Build contingency table
    # b=0, b=1
    # a=0: n00, n01  (a wrong)
    # a=1: n10, n11  (a right)
    n01 = sum(1 for a, b in zip(correct_a, correct_b, strict=True) if not a and b)
    n10 = sum(1 for a, b in zip(correct_a, correct_b, strict=True) if a and not b)

    # McNemar's chi-squared statistic
    if n01 + n10 == 0:
        return (0.0, 1.0)  # No discordant pairs

    chi2 = (abs(n01 - n10) - 1) ** 2 / (n01 + n10)
    p_value = 1 - stats.chi2.cdf(chi2, df=1)

    return (float(chi2), float(p_value))


def wilcoxon_test(
    scores_a: Sequence[float],
    scores_b: Sequence[float],
) -> tuple[float, float]:
    """Wilcoxon signed-rank test for paired continuous outcomes.

    Tests whether paired samples have different medians.
    Used for comparing F-scores, Jaccard, etc.

    Args:
        scores_a: Scores for system A.
        scores_b: Scores for system B.

    Returns:
        Tuple of (statistic, p_value).
    """
    # Handle edge cases
    if len(scores_a) < 10:
        # Too few samples for reliable test
        return (0.0, 1.0)

    differences = np.array(scores_a) - np.array(scores_b)

    # Remove zero differences (ties)
    nonzero_diff = differences[differences != 0]
    if len(nonzero_diff) == 0:
        return (0.0, 1.0)  # All ties

    result = stats.wilcoxon(nonzero_diff, alternative="two-sided")
    return (float(result.statistic), float(result.pvalue))


def benjamini_hochberg(
    p_values: Sequence[float],
    alpha: float = 0.05,
) -> list[bool]:
    """Benjamini-Hochberg procedure for multiple comparison correction.

    Controls the false discovery rate (FDR) when performing multiple
    hypothesis tests.

    Args:
        p_values: List of p-values from multiple tests.
        alpha: Desired FDR level (default: 0.05).

    Returns:
        List of booleans indicating which tests are significant.
    """
    n = len(p_values)
    if n == 0:
        return []

    # Sort p-values and track original indices
    indexed_pvals = sorted(enumerate(p_values), key=lambda x: x[1])

    # Apply BH correction
    significant = [False] * n
    for rank, (orig_idx, pval) in enumerate(indexed_pvals, start=1):
        # BH threshold: (rank / n) * alpha
        threshold = (rank / n) * alpha
        if pval <= threshold:
            # Mark this and all smaller p-values as significant
            for j in range(rank):
                significant[indexed_pvals[j][0]] = True

    return significant


def cohens_d(
    group_a: Sequence[float],
    group_b: Sequence[float],
) -> float:
    """Compute Cohen's d effect size.

    Interpretation:
    - 0.2: small effect
    - 0.5: medium effect
    - 0.8: large effect

    Args:
        group_a: Scores for group A.
        group_b: Scores for group B.

    Returns:
        Cohen's d effect size.
    """
    a = np.array(group_a)
    b = np.array(group_b)

    n_a, n_b = len(a), len(b)
    var_a, var_b = np.var(a, ddof=1), np.var(b, ddof=1)

    # Pooled standard deviation
    pooled_std = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))

    if pooled_std == 0:
        return 0.0

    return float((np.mean(a) - np.mean(b)) / pooled_std)


def format_result(
    metric_name: str,
    value: float,
    ci: tuple[float, float] | None = None,
    baseline_value: float | None = None,
    p_value: float | None = None,
    effect_size: float | None = None,
) -> str:
    """Format a result following the thesis reporting template.

    Template: "Performance: 87.3% F2 (95% CI: 85.1-89.5)
               Comparison: +3.2% vs. baseline (p < 0.001, Cohen's d = 0.65)"

    Args:
        metric_name: Name of the metric (e.g., "F2").
        value: Metric value.
        ci: Optional confidence interval.
        baseline_value: Optional baseline for comparison.
        p_value: Optional p-value from significance test.
        effect_size: Optional Cohen's d.

    Returns:
        Formatted result string.
    """
    # Format main result
    if ci is not None:
        result = f"Performance: {value:.1%} {metric_name} (95% CI: {ci[0]:.1%}-{ci[1]:.1%})"
    else:
        result = f"Performance: {value:.1%} {metric_name}"

    # Add comparison if baseline provided
    if baseline_value is not None:
        diff = value - baseline_value
        sign = "+" if diff >= 0 else ""
        comparison = f"Comparison: {sign}{diff:.1%} vs. baseline"

        if p_value is not None:
            if p_value < 0.001:
                comparison += " (p < 0.001"
            else:
                comparison += f" (p = {p_value:.3f}"

            if effect_size is not None:
                comparison += f", Cohen's d = {effect_size:.2f})"
            else:
                comparison += ")"

        result += f"\n{comparison}"

    return result
