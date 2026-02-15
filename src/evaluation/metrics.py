"""Evaluation metrics for contract clause extraction.

Implements metrics from ContractEval paper:
- F1, F2 scores
- Jaccard similarity
- Laziness rate (false "no related clause")
- Grounding rate (extracted text in source)

TP/FP/FN Definitions (from ContractEval):
- TP: Label not empty AND prediction fully covers labeled span
- TN: Label empty AND model predicts "no related clause"
- FP: Label empty BUT model predicts non-empty clause
- FN: Label not empty BUT model outputs "no related clause" OR fails to cover span
"""

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


@dataclass
class EvaluationResult:
    """Complete evaluation results for an experiment."""

    # Primary metrics
    f1: float = 0.0
    f2: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    jaccard: float = 0.0

    # Error analysis
    laziness_rate: float = 0.0  # False "no related clause" rate
    grounding_rate: float = 0.0  # Extracted text found in source
    hallucination_rate: float = 0.0  # Extracted text not in source

    # Counts
    tp: int = 0
    tn: int = 0
    fp: int = 0
    fn: int = 0

    # Per-category breakdown
    category_scores: dict[str, dict[str, float]] = field(default_factory=dict)

    # Confidence intervals (populated by statistical analysis)
    f1_ci: tuple[float, float] | None = None
    f2_ci: tuple[float, float] | None = None


def compute_precision(tp: int, fp: int) -> float:
    """Compute precision = TP / (TP + FP).

    Args:
        tp: True positives count.
        fp: False positives count.

    Returns:
        Precision score (0-1).
    """
    if tp + fp == 0:
        return 0.0
    return tp / (tp + fp)


def compute_recall(tp: int, fn: int) -> float:
    """Compute recall = TP / (TP + FN).

    Args:
        tp: True positives count.
        fn: False negatives count.

    Returns:
        Recall score (0-1).
    """
    if tp + fn == 0:
        return 0.0
    return tp / (tp + fn)


def compute_f1(tp: int, fp: int, fn: int) -> float:
    """Compute F1 score = 2 * (P * R) / (P + R).

    Args:
        tp: True positives count.
        fp: False positives count.
        fn: False negatives count.

    Returns:
        F1 score (0-1).
    """
    precision = compute_precision(tp, fp)
    recall = compute_recall(tp, fn)
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def compute_f2(tp: int, fp: int, fn: int) -> float:
    """Compute F2 score = 5 * (P * R) / (4P + R).

    F2 weights recall higher than precision (beta=2).
    This is appropriate for contract extraction where
    missing a clause (FN) is worse than extracting extra text (FP).

    Args:
        tp: True positives count.
        fp: False positives count.
        fn: False negatives count.

    Returns:
        F2 score (0-1).
    """
    precision = compute_precision(tp, fp)
    recall = compute_recall(tp, fn)
    if 4 * precision + recall == 0:
        return 0.0
    return 5 * (precision * recall) / (4 * precision + recall)


def compute_jaccard(prediction: str, ground_truth: str) -> float:
    """Compute Jaccard similarity between prediction and ground truth.

    Jaccard = |A ∩ B| / |A ∪ B| where A and B are token sets.

    Args:
        prediction: Predicted text.
        ground_truth: Ground truth text.

    Returns:
        Jaccard similarity (0-1).
    """
    if not prediction and not ground_truth:
        return 1.0  # Both empty = perfect match
    if not prediction or not ground_truth:
        return 0.0  # One empty = no overlap

    pred_tokens = set(prediction.lower().split())
    truth_tokens = set(ground_truth.lower().split())

    intersection = pred_tokens & truth_tokens
    union = pred_tokens | truth_tokens

    if len(union) == 0:
        return 0.0

    return len(intersection) / len(union)


def compute_laziness_rate(
    predictions: Sequence[str],
    labels: Sequence[str],
) -> float:
    """Compute laziness rate: false "no related clause" responses.

    Laziness = FN("no clause") / Total Positive Labels

    This measures how often the model incorrectly says "no related clause"
    when there actually is a relevant clause in the contract.

    Args:
        predictions: List of model predictions.
        labels: List of ground truth labels.

    Returns:
        Laziness rate (0-1). Target: < 3%.
    """
    total_positive = 0
    lazy_responses = 0

    for pred, label in zip(predictions, labels, strict=True):
        # Label is not empty = there should be a clause
        if label.strip():
            total_positive += 1
            # Model said "no related clause" when there was one
            if _is_no_clause_response(pred):
                lazy_responses += 1

    if total_positive == 0:
        return 0.0

    return lazy_responses / total_positive


def _is_no_clause_response(response: str) -> bool:
    """Check if response indicates no clause found.

    Args:
        response: Model response text.

    Returns:
        True if response indicates no clause.
    """
    normalized = response.strip().lower()
    no_clause_patterns = [
        "no related clause",
        "no related clause.",
        "no relevant clause",
        "none found",
        "not found",
        "n/a",
    ]
    return normalized in no_clause_patterns or not normalized


def compute_grounding_rate(
    extracted_clauses: Sequence[str],
    contract_text: str,
) -> float:
    """Compute grounding rate: extracted text found in source.

    Grounding = Clauses found in source / Total extracted clauses

    Args:
        extracted_clauses: List of extracted clause texts.
        contract_text: Original contract text.

    Returns:
        Grounding rate (0-1). Target: > 95%.
    """
    if not extracted_clauses:
        return 1.0  # No extractions = vacuously grounded

    grounded = 0
    normalized_contract = " ".join(contract_text.split()).lower()

    for clause in extracted_clauses:
        normalized_clause = " ".join(clause.split()).lower()
        if normalized_clause in normalized_contract:
            grounded += 1

    return grounded / len(extracted_clauses)


def span_overlap(pred_span: str, truth_span: str) -> bool:
    """Check if prediction fully covers the ground truth span.

    Following ContractEval: TP requires prediction to fully cover labeled span.

    Args:
        pred_span: Predicted clause text.
        truth_span: Ground truth clause text.

    Returns:
        True if prediction covers ground truth.
    """
    if not truth_span.strip():
        return False

    # Normalize whitespace
    pred_normalized = " ".join(pred_span.split()).lower()
    truth_normalized = " ".join(truth_span.split()).lower()

    # Check if truth is contained in prediction
    return truth_normalized in pred_normalized


def evaluate_single(
    prediction: str,
    ground_truth: str,
    contract_text: str,
) -> dict[str, int | float]:
    """Evaluate a single prediction against ground truth.

    Args:
        prediction: Model prediction.
        ground_truth: Ground truth label.
        contract_text: Original contract for grounding check.

    Returns:
        Dict with tp, tn, fp, fn, jaccard, grounded.
    """
    pred_empty = _is_no_clause_response(prediction)
    truth_empty = not ground_truth.strip()

    result: dict[str, int | float] = {
        "tp": 0,
        "tn": 0,
        "fp": 0,
        "fn": 0,
        "jaccard": 0.0,
        "grounded": 1.0,
    }

    if truth_empty and pred_empty:
        # TN: Both empty
        result["tn"] = 1
        result["jaccard"] = 1.0
    elif truth_empty and not pred_empty:
        # FP: Truth empty but prediction not
        result["fp"] = 1
        result["jaccard"] = 0.0
        result["grounded"] = compute_grounding_rate([prediction], contract_text)
    elif not truth_empty and pred_empty:
        # FN: Truth not empty but prediction empty (laziness)
        result["fn"] = 1
        result["jaccard"] = 0.0
    else:
        # Both not empty - check span coverage
        if span_overlap(prediction, ground_truth):
            result["tp"] = 1
        else:
            result["fn"] = 1
        result["jaccard"] = compute_jaccard(prediction, ground_truth)
        result["grounded"] = compute_grounding_rate([prediction], contract_text)

    return result


def evaluate_batch(
    predictions: Sequence[str],
    ground_truths: Sequence[str],
    contract_texts: Sequence[str],
    categories: Sequence[str] | None = None,
) -> EvaluationResult:
    """Evaluate a batch of predictions.

    Args:
        predictions: List of model predictions.
        ground_truths: List of ground truth labels.
        contract_texts: List of original contracts.
        categories: Optional list of category names for breakdown.

    Returns:
        Complete EvaluationResult with all metrics.
    """
    tp = tn = fp = fn = 0
    jaccard_scores: list[float] = []
    grounding_scores: list[float] = []
    category_results: dict[str, list[dict[str, int | float]]] = {}

    for i, (pred, truth, contract) in enumerate(
        zip(predictions, ground_truths, contract_texts, strict=True)
    ):
        result = evaluate_single(pred, truth, contract)
        tp += result["tp"]
        tn += result["tn"]
        fp += result["fp"]
        fn += result["fn"]
        jaccard_scores.append(result["jaccard"])
        grounding_scores.append(result["grounded"])

        # Track per-category
        if categories is not None:
            cat = categories[i]
            if cat not in category_results:
                category_results[cat] = []
            category_results[cat].append(result)

    # Compute aggregate metrics
    precision = compute_precision(tp, fp)
    recall = compute_recall(tp, fn)
    f1 = compute_f1(precision, recall)
    f2 = compute_f2(precision, recall)
    jaccard = float(np.mean(jaccard_scores)) if jaccard_scores else 0.0
    grounding = float(np.mean(grounding_scores)) if grounding_scores else 1.0
    laziness = compute_laziness_rate(predictions, ground_truths)

    # Compute per-category scores
    category_scores: dict[str, dict[str, float]] = {}
    for cat, results in category_results.items():
        cat_tp = sum(r["tp"] for r in results)
        cat_fp = sum(r["fp"] for r in results)
        cat_fn = sum(r["fn"] for r in results)
        cat_precision = compute_precision(int(cat_tp), int(cat_fp))
        cat_recall = compute_recall(int(cat_tp), int(cat_fn))
        category_scores[cat] = {
            "f1": compute_f1(cat_precision, cat_recall),
            "f2": compute_f2(cat_precision, cat_recall),
            "precision": cat_precision,
            "recall": cat_recall,
            "jaccard": float(np.mean([r["jaccard"] for r in results])),
        }

    return EvaluationResult(
        f1=f1,
        f2=f2,
        precision=precision,
        recall=recall,
        jaccard=jaccard,
        laziness_rate=laziness,
        grounding_rate=grounding,
        hallucination_rate=1.0 - grounding,
        tp=tp,
        tn=tn,
        fp=fp,
        fn=fn,
        category_scores=category_scores,
    )
