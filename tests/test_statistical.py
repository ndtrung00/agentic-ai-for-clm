"""Tests for statistical analysis functions."""

import pytest
import numpy as np

from src.evaluation.statistical import (
    bootstrap_ci,
    mcnemar_test,
    wilcoxon_test,
    benjamini_hochberg,
    cohens_d,
    format_result,
)


class TestBootstrapCI:
    """Tests for bootstrap confidence intervals."""

    def test_bootstrap_deterministic(self):
        """Test bootstrap with fixed random state."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        ci1 = bootstrap_ci(data, random_state=42)
        ci2 = bootstrap_ci(data, random_state=42)
        assert ci1 == ci2

    def test_bootstrap_reasonable_bounds(self):
        """Test that CI bounds are reasonable."""
        data = list(np.random.normal(0.5, 0.1, 100))
        lower, upper = bootstrap_ci(data)
        assert lower < upper
        assert lower > 0
        assert upper < 1

    def test_bootstrap_custom_statistic(self):
        """Test bootstrap with custom statistic."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        ci = bootstrap_ci(data, statistic=np.median)
        assert ci[0] <= 3.0 <= ci[1]


class TestMcNemarTest:
    """Tests for McNemar's test."""

    def test_mcnemar_identical(self):
        """Test McNemar with identical outcomes."""
        correct = [True, True, False, False]
        chi2, p_value = mcnemar_test(correct, correct)
        assert p_value == 1.0

    def test_mcnemar_different(self):
        """Test McNemar with different outcomes."""
        # System B is better on many discordant pairs (n01=19, n10=0)
        correct_a = [True] + [False] * 19
        correct_b = [True] * 20
        chi2, p_value = mcnemar_test(correct_a, correct_b)
        assert p_value < 0.05

    def test_mcnemar_no_discordant(self):
        """Test McNemar with no discordant pairs."""
        correct_a = [True, True, True]
        correct_b = [True, True, True]
        chi2, p_value = mcnemar_test(correct_a, correct_b)
        assert p_value == 1.0


class TestWilcoxonTest:
    """Tests for Wilcoxon signed-rank test."""

    def test_wilcoxon_insufficient_data(self):
        """Test Wilcoxon with too few samples."""
        scores_a = [0.5, 0.6, 0.7]
        scores_b = [0.6, 0.7, 0.8]
        stat, p_value = wilcoxon_test(scores_a, scores_b)
        assert p_value == 1.0  # Not enough data

    def test_wilcoxon_significant_difference(self):
        """Test Wilcoxon with significant difference."""
        # B is consistently better
        scores_a = list(np.random.normal(0.5, 0.1, 30))
        scores_b = [s + 0.3 for s in scores_a]  # B is 0.3 better
        stat, p_value = wilcoxon_test(scores_a, scores_b)
        assert p_value < 0.05


class TestBenjaminiHochberg:
    """Tests for Benjamini-Hochberg correction."""

    def test_bh_empty(self):
        """Test BH with empty p-values."""
        result = benjamini_hochberg([])
        assert result == []

    def test_bh_all_significant(self):
        """Test BH with all significant p-values."""
        p_values = [0.001, 0.002, 0.003]
        result = benjamini_hochberg(p_values, alpha=0.05)
        assert all(result)

    def test_bh_none_significant(self):
        """Test BH with no significant p-values."""
        p_values = [0.5, 0.6, 0.7]
        result = benjamini_hochberg(p_values, alpha=0.05)
        assert not any(result)

    def test_bh_mixed(self):
        """Test BH with mixed significance."""
        p_values = [0.001, 0.5, 0.01]
        result = benjamini_hochberg(p_values, alpha=0.05)
        # First and third should be significant after correction
        assert result[0] is True
        assert result[2] is True


class TestCohensD:
    """Tests for Cohen's d effect size."""

    def test_cohens_d_identical(self):
        """Test Cohen's d with identical groups."""
        group = [1.0, 2.0, 3.0, 4.0, 5.0]
        d = cohens_d(group, group)
        assert d == 0.0

    def test_cohens_d_large_effect(self):
        """Test Cohen's d with large effect."""
        group_a = [1.0, 1.5, 2.0, 2.5, 3.0]
        group_b = [4.0, 4.5, 5.0, 5.5, 6.0]
        d = cohens_d(group_a, group_b)
        # Large negative effect (A < B)
        assert abs(d) > 0.8

    def test_cohens_d_sign(self):
        """Test Cohen's d sign convention."""
        group_a = [4.5, 5.0, 5.5]
        group_b = [0.5, 1.0, 1.5]
        d = cohens_d(group_a, group_b)
        # A > B, so d should be positive
        assert d > 0


class TestFormatResult:
    """Tests for result formatting."""

    def test_format_simple(self):
        """Test simple result formatting."""
        result = format_result("F2", 0.75)
        assert "75.0%" in result
        assert "F2" in result

    def test_format_with_ci(self):
        """Test formatting with confidence interval."""
        result = format_result("F2", 0.75, ci=(0.70, 0.80))
        assert "95% CI" in result
        assert "70.0%" in result
        assert "80.0%" in result

    def test_format_with_comparison(self):
        """Test formatting with baseline comparison."""
        result = format_result(
            "F2",
            0.75,
            baseline_value=0.68,
            p_value=0.01,
            effect_size=0.65,
        )
        assert "Comparison" in result
        assert "+7.0%" in result
        assert "p = 0.010" in result
        assert "Cohen's d = 0.65" in result
