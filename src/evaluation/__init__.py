"""Evaluation metrics and statistical analysis."""

from src.evaluation.metrics import (
    compute_f1,
    compute_f2,
    compute_jaccard,
    compute_laziness_rate,
    compute_grounding_rate,
    evaluate_batch,
    evaluate_single,
    EvaluationResult,
)
from src.evaluation.statistical import (
    bootstrap_ci,
    mcnemar_test,
    wilcoxon_test,
    benjamini_hochberg,
    cohens_d,
)

__all__ = [
    "compute_f1",
    "compute_f2",
    "compute_jaccard",
    "compute_laziness_rate",
    "compute_grounding_rate",
    "evaluate_batch",
    "evaluate_single",
    "EvaluationResult",
    "bootstrap_ci",
    "mcnemar_test",
    "wilcoxon_test",
    "benjamini_hochberg",
    "cohens_d",
]
