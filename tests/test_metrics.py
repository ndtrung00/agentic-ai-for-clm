"""Tests for evaluation metrics."""

import pytest

from src.evaluation.metrics import (
    compute_precision,
    compute_recall,
    compute_f1,
    compute_f2,
    compute_jaccard,
    compute_laziness_rate,
    compute_grounding_rate,
    span_overlap,
    evaluate_single,
    evaluate_batch,
)


class TestBasicMetrics:
    """Tests for precision, recall, F1, F2."""

    def test_precision_perfect(self):
        """Test precision with no false positives."""
        assert compute_precision(10, 0) == 1.0

    def test_precision_half(self):
        """Test precision at 50%."""
        assert compute_precision(5, 5) == 0.5

    def test_precision_zero_denominator(self):
        """Test precision with no predictions."""
        assert compute_precision(0, 0) == 0.0

    def test_recall_perfect(self):
        """Test recall with no false negatives."""
        assert compute_recall(10, 0) == 1.0

    def test_recall_half(self):
        """Test recall at 50%."""
        assert compute_recall(5, 5) == 0.5

    def test_recall_zero_denominator(self):
        """Test recall with no positives."""
        assert compute_recall(0, 0) == 0.0

    def test_f1_perfect(self):
        """Test F1 with perfect precision and recall."""
        assert compute_f1(1.0, 1.0) == 1.0

    def test_f1_zero(self):
        """Test F1 with zero precision or recall."""
        assert compute_f1(0.0, 1.0) == 0.0
        assert compute_f1(1.0, 0.0) == 0.0
        assert compute_f1(0.0, 0.0) == 0.0

    def test_f1_balanced(self):
        """Test F1 with equal precision and recall."""
        assert compute_f1(0.5, 0.5) == 0.5

    def test_f2_weights_recall(self):
        """Test that F2 weights recall higher than precision."""
        # Same precision, different recall
        f2_high_recall = compute_f2(0.5, 0.9)
        f2_low_recall = compute_f2(0.5, 0.3)
        assert f2_high_recall > f2_low_recall

    def test_f2_formula(self):
        """Test F2 formula: 5 * (P * R) / (4P + R)."""
        p, r = 0.8, 0.6
        expected = 5 * (p * r) / (4 * p + r)
        assert abs(compute_f2(p, r) - expected) < 1e-10


class TestJaccard:
    """Tests for Jaccard similarity."""

    def test_jaccard_identical(self):
        """Test Jaccard with identical strings."""
        assert compute_jaccard("hello world", "hello world") == 1.0

    def test_jaccard_empty_both(self):
        """Test Jaccard with both empty."""
        assert compute_jaccard("", "") == 1.0

    def test_jaccard_one_empty(self):
        """Test Jaccard with one empty."""
        assert compute_jaccard("hello", "") == 0.0
        assert compute_jaccard("", "hello") == 0.0

    def test_jaccard_partial_overlap(self):
        """Test Jaccard with partial overlap."""
        # "hello world" vs "hello there" shares "hello"
        result = compute_jaccard("hello world", "hello there")
        # Intersection: {"hello"}, Union: {"hello", "world", "there"}
        assert result == 1 / 3

    def test_jaccard_case_insensitive(self):
        """Test that Jaccard is case insensitive."""
        assert compute_jaccard("Hello World", "hello world") == 1.0


class TestLazinessRate:
    """Tests for laziness rate (false 'no related clause')."""

    def test_laziness_no_positives(self):
        """Test laziness with no positive labels."""
        predictions = ["", "no related clause"]
        labels = ["", ""]
        assert compute_laziness_rate(predictions, labels) == 0.0

    def test_laziness_all_correct(self):
        """Test laziness with no lazy responses."""
        predictions = ["some clause", "another clause"]
        labels = ["some clause", "another clause"]
        assert compute_laziness_rate(predictions, labels) == 0.0

    def test_laziness_all_lazy(self):
        """Test laziness with all lazy responses."""
        predictions = ["no related clause.", "no related clause."]
        labels = ["some clause", "another clause"]
        assert compute_laziness_rate(predictions, labels) == 1.0

    def test_laziness_partial(self):
        """Test laziness with some lazy responses."""
        predictions = ["some clause", "no related clause."]
        labels = ["some clause", "another clause"]
        assert compute_laziness_rate(predictions, labels) == 0.5


class TestGroundingRate:
    """Tests for grounding rate (extracted text in source)."""

    def test_grounding_empty_extractions(self):
        """Test grounding with no extractions."""
        assert compute_grounding_rate([], "some contract text") == 1.0

    def test_grounding_all_grounded(self):
        """Test grounding with all clauses in source."""
        contract = "This is the contract. It contains a liability clause."
        clauses = ["liability clause", "the contract"]
        assert compute_grounding_rate(clauses, contract) == 1.0

    def test_grounding_none_grounded(self):
        """Test grounding with no clauses in source."""
        contract = "This is the contract."
        clauses = ["hallucinated text", "made up clause"]
        assert compute_grounding_rate(clauses, contract) == 0.0

    def test_grounding_partial(self):
        """Test grounding with some clauses in source."""
        contract = "This is the contract."
        clauses = ["the contract", "hallucinated text"]
        assert compute_grounding_rate(clauses, contract) == 0.5


class TestSpanOverlap:
    """Tests for span overlap checking."""

    def test_span_overlap_exact(self):
        """Test span overlap with exact match."""
        assert span_overlap("hello world", "hello world") is True

    def test_span_overlap_contains(self):
        """Test span overlap when prediction contains truth."""
        assert span_overlap("hello beautiful world", "beautiful") is True

    def test_span_overlap_no_match(self):
        """Test span overlap with no match."""
        assert span_overlap("hello world", "goodbye") is False

    def test_span_overlap_empty_truth(self):
        """Test span overlap with empty ground truth."""
        assert span_overlap("hello world", "") is False
        assert span_overlap("hello world", "   ") is False


class TestEvaluateSingle:
    """Tests for single sample evaluation."""

    def test_evaluate_single_tp(self):
        """Test true positive case."""
        result = evaluate_single(
            prediction="The liability is capped at $1M.",
            ground_truth="capped at $1M",
            contract_text="The liability is capped at $1M.",
        )
        assert result["tp"] == 1
        assert result["tn"] == 0
        assert result["fp"] == 0
        assert result["fn"] == 0

    def test_evaluate_single_tn(self):
        """Test true negative case."""
        result = evaluate_single(
            prediction="no related clause.",
            ground_truth="",
            contract_text="Some contract text.",
        )
        assert result["tn"] == 1

    def test_evaluate_single_fp(self):
        """Test false positive case."""
        result = evaluate_single(
            prediction="Some extracted text.",
            ground_truth="",
            contract_text="Some extracted text.",
        )
        assert result["fp"] == 1

    def test_evaluate_single_fn_lazy(self):
        """Test false negative (lazy) case."""
        result = evaluate_single(
            prediction="no related clause.",
            ground_truth="actual clause here",
            contract_text="The actual clause here is important.",
        )
        assert result["fn"] == 1


class TestEvaluateBatch:
    """Tests for batch evaluation."""

    def test_evaluate_batch_perfect(self):
        """Test batch evaluation with perfect predictions."""
        predictions = ["clause A", "clause B"]
        ground_truths = ["clause A", "clause B"]
        contracts = ["clause A is here", "clause B is here"]
        categories = ["cat1", "cat2"]

        result = evaluate_batch(predictions, ground_truths, contracts, categories)
        assert result.tp == 2
        assert result.precision == 1.0
        assert result.recall == 1.0

    def test_evaluate_batch_category_breakdown(self):
        """Test that category scores are computed."""
        predictions = ["clause A", "no related clause."]
        ground_truths = ["clause A", "clause B"]
        contracts = ["clause A is here", "clause B is here"]
        categories = ["cat1", "cat1"]

        result = evaluate_batch(predictions, ground_truths, contracts, categories)
        assert "cat1" in result.category_scores
