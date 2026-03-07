"""Shared logic for computing, printing, and saving experiment results.

Used by both notebook 03 (baselines) and notebook 04 (multi-agent) to avoid
duplication of metrics computation, diagnostics printing, and summary JSON
construction.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from src.evaluation.metrics import (
    compute_f1,
    compute_f2,
    compute_precision,
    compute_recall,
)
from src.models.diagnostics import ModelDiagnostics


def compute_aggregate_metrics(results: list[dict]) -> dict[str, Any]:
    """Compute tp/fp/fn/tn, precision, recall, f1, f2, avg_jaccard, laziness_rate.

    Args:
        results: List of per-sample result dicts (must have ``evaluation`` and
            ``output`` / ``ground_truth`` sub-dicts).

    Returns:
        Dict with keys: tp, fp, fn, tn, precision, recall, f1, f2,
        avg_jaccard, laziness_rate.
    """
    tp = sum(1 for r in results if r["evaluation"]["classification"] == "TP")
    fp = sum(1 for r in results if r["evaluation"]["classification"] == "FP")
    fn = sum(1 for r in results if r["evaluation"]["classification"] == "FN")
    tn = sum(1 for r in results if r["evaluation"]["classification"] == "TN")

    total_positive = tp + fn
    laziness_count = sum(
        1 for r in results
        if r["evaluation"]["classification"] == "FN"
        and r["output"]["num_clauses"] == 0
    )

    precision = compute_precision(tp, fp)
    recall = compute_recall(tp, fn)
    f1 = compute_f1(tp, fp, fn)
    f2 = compute_f2(tp, fp, fn)

    jaccard_scores = [
        r["evaluation"]["jaccard"]
        for r in results
        if r["ground_truth"]["has_clause"]
    ]
    span_coverage_scores = [
        r["evaluation"]["span_coverage"]
        for r in results
        if r["ground_truth"]["has_clause"] and "span_coverage" in r["evaluation"]
    ]
    containment_scores = [
        r["evaluation"]["containment"]
        for r in results
        if r["ground_truth"]["has_clause"] and "containment" in r["evaluation"]
    ]
    avg_jaccard = sum(jaccard_scores) / len(jaccard_scores) if jaccard_scores else 0.0
    avg_span_coverage = (
        sum(span_coverage_scores) / len(span_coverage_scores)
        if span_coverage_scores
        else 0.0
    )
    avg_containment = (
        sum(containment_scores) / len(containment_scores)
        if containment_scores
        else 0.0
    )
    laziness_rate = laziness_count / total_positive if total_positive > 0 else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "f2": f2,
        "avg_jaccard": avg_jaccard,
        "avg_span_coverage": avg_span_coverage,
        "avg_containment": avg_containment,
        "laziness_rate": laziness_rate,
    }


def compute_per_tier_metrics(results: list[dict]) -> dict[str, dict[str, Any]]:
    """Compute per-tier breakdown (common / moderate / rare).

    Args:
        results: List of per-sample result dicts.

    Returns:
        ``{tier: {tp, fp, fn, tn, f1, f2, avg_jaccard}}`` for each tier.
    """
    per_tier: dict[str, dict[str, Any]] = {}
    for tier in ["common", "moderate", "rare"]:
        tr = [r for r in results if r["tier"] == tier]
        t_tp = sum(1 for r in tr if r["evaluation"]["classification"] == "TP")
        t_fp = sum(1 for r in tr if r["evaluation"]["classification"] == "FP")
        t_fn = sum(1 for r in tr if r["evaluation"]["classification"] == "FN")
        t_tn = sum(1 for r in tr if r["evaluation"]["classification"] == "TN")
        t_jaccs = [
            r["evaluation"]["jaccard"]
            for r in tr
            if r["ground_truth"]["has_clause"]
        ]
        t_span_covs = [
            r["evaluation"]["span_coverage"]
            for r in tr
            if r["ground_truth"]["has_clause"] and "span_coverage" in r["evaluation"]
        ]
        t_containments = [
            r["evaluation"]["containment"]
            for r in tr
            if r["ground_truth"]["has_clause"] and "containment" in r["evaluation"]
        ]
        per_tier[tier] = {
            "tp": t_tp,
            "fp": t_fp,
            "fn": t_fn,
            "tn": t_tn,
            "f1": compute_f1(t_tp, t_fp, t_fn),
            "f2": compute_f2(t_tp, t_fp, t_fn),
            "avg_jaccard": sum(t_jaccs) / len(t_jaccs) if t_jaccs else 0.0,
            "avg_span_coverage": sum(t_span_covs) / len(t_span_covs) if t_span_covs else 0.0,
            "avg_containment": sum(t_containments) / len(t_containments) if t_containments else 0.0,
        }
    return per_tier


def print_metrics(
    metrics: dict[str, Any],
    per_tier: dict[str, dict[str, Any]],
    *,
    run_type: str,
    run_label: str,
    model_key: str,
) -> None:
    """Print formatted aggregate metrics and per-tier breakdown.

    Args:
        metrics: Output of :func:`compute_aggregate_metrics`.
        per_tier: Output of :func:`compute_per_tier_metrics`.
        run_type: Short identifier like ``"B1"`` or ``"M1"``.
        run_label: Human-readable label like ``"zero_shot"`` or ``"multiagent"``.
        model_key: Model registry key.
    """
    total_samples = metrics["tp"] + metrics["fp"] + metrics["fn"] + metrics["tn"]

    print(f"{'=' * 60}")
    print(f"  {run_type} {run_label} — {model_key}")
    print(f"{'=' * 60}")
    print(f"  Samples:       {total_samples}")
    print(f"  TP: {metrics['tp']}  FP: {metrics['fp']}  FN: {metrics['fn']}  TN: {metrics['tn']}")
    print()
    print(f"  Precision:     {metrics['precision']:.3f}")
    print(f"  Recall:        {metrics['recall']:.3f}")
    print(f"  F1:            {metrics['f1']:.3f}")
    print(f"  F2:            {metrics['f2']:.3f}")
    print(f"  Avg Jaccard:   {metrics['avg_jaccard']:.3f}")
    print(f"  Containment:   {metrics['avg_containment']:.3f}")
    print(f"  Span Coverage: {metrics['avg_span_coverage']:.3f}")
    print(f"  Laziness rate: {metrics['laziness_rate']:.1%} "
          f"({int(metrics['laziness_rate'] * (metrics['tp'] + metrics['fn']))}/"
          f"{metrics['tp'] + metrics['fn']})")
    print()
    print(f"  ContractEval reference (GPT-4.1):")
    print(f"  F1=0.641  F2=0.678  Jaccard=0.472  Laziness=7.1%")

    # Per-tier table
    print(f"\n{'=' * 70}")
    print(f"  Per-Tier Breakdown")
    print(f"{'=' * 70}")
    print(f"  {'Tier':<10} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4} {'F1':>7} {'F2':>7} {'Jaccard':>8} {'Contain':>8} {'SpanCov':>8}")
    print(f"  {'-' * 78}")

    for tier in ["common", "moderate", "rare"]:
        t = per_tier[tier]
        print(
            f"  {tier:<10} {t['tp']:>4} {t['fp']:>4} {t['fn']:>4} {t['tn']:>4} "
            f"{t['f1']:>7.3f} {t['f2']:>7.3f} {t['avg_jaccard']:>8.3f} "
            f"{t['avg_containment']:>8.3f} {t['avg_span_coverage']:>8.3f}"
        )


def print_diagnostics(diagnostics: ModelDiagnostics, model_key: str) -> dict[str, Any]:
    """Print diagnostics summary and return the summary dict.

    Args:
        diagnostics: :class:`ModelDiagnostics` instance.
        model_key: Model registry key (for display).

    Returns:
        The diagnostics summary dict (from ``diagnostics.summary()``).
    """
    diag_summary = diagnostics.summary()

    print(f"Model Diagnostics ({model_key})")
    print("=" * 50)
    print(f"API calls:       {diag_summary['total_calls']}")
    print(f"Success rate:    {diag_summary['success_rate']:.0%}")
    print(f"Input tokens:    {diag_summary['total_input_tokens']:,}")
    print(f"Output tokens:   {diag_summary['total_output_tokens']:,}")
    print(f"Total tokens:    {diag_summary['total_tokens']:,}")
    print(f"Estimated cost:  ${diag_summary['total_cost_usd']:.4f}")
    print(f"Avg latency:     {diag_summary['avg_latency_ms']:.0f} ms")
    print(f"Total time:      {diag_summary['duration_seconds']:.1f} s")

    if diag_summary["total_calls"] > 0:
        avg_in = diag_summary["total_input_tokens"] / diag_summary["total_calls"]
        avg_out = diag_summary["total_output_tokens"] / diag_summary["total_calls"]
        print(f"\nAvg tokens/call: {avg_in:,.0f} in / {avg_out:,.0f} out")

    # Per-agent breakdown (useful for M1 to see specialist distribution)
    if diag_summary.get("by_agent"):
        print(f"\nCalls by agent:")
        for agent, count in sorted(diag_summary["by_agent"].items()):
            print(f"  {agent:25s}: {count}")

    return diag_summary


def save_experiment(
    *,
    run_id: str,
    results: list[dict],
    metrics: dict[str, Any],
    per_tier: dict[str, dict[str, Any]],
    diag_summary: dict[str, Any],
    diagnostics: ModelDiagnostics,
    model_key: str,
    config: Any,
    run_type: str,
    run_label: str,
    intermediate_path: Path | str,
    temperature: float,
    max_tokens: int,
    samples_per_tier: int,
    max_contract_chars: int,
    include_negative: bool,
    prompt: dict[str, Any] | None = None,
    architecture: dict[str, Any] | None = None,
    is_official: bool = False,
) -> tuple[Path, Path]:
    """Build summary JSON and save summary + diagnostics files.

    When *prompt* is provided the summary uses ``baseline_type`` / ``baseline_label``.
    When *architecture* is provided it uses ``experiment_type`` / ``experiment_label``.

    Args:
        run_id: Unique run identifier.
        results: Per-sample result dicts.
        metrics: Output of :func:`compute_aggregate_metrics`.
        per_tier: Output of :func:`compute_per_tier_metrics`.
        diag_summary: Output of :func:`print_diagnostics`.
        diagnostics: :class:`ModelDiagnostics` for raw export.
        model_key: Model registry key (e.g. ``"gpt-4.1-mini"``).
        config: :class:`ModelConfig` object.
        run_type: Short identifier (``"B1"`` / ``"M1"`` etc.).
        run_label: Label (``"zero_shot"`` / ``"multiagent"`` etc.).
        intermediate_path: Path to intermediate JSONL (recorded in summary).
        temperature: Generation temperature used.
        max_tokens: Max output tokens used.
        samples_per_tier: Samples per tier used.
        max_contract_chars: Contract char limit used.
        include_negative: Whether negative samples were included.
        prompt: Baseline prompt info dict (notebook 03). Mutually exclusive
            with *architecture*.
        architecture: Multi-agent architecture dict (notebook 04). Mutually
            exclusive with *prompt*.

    Returns:
        ``(summary_path, diagnostics_path)``
    """
    intermediate_path = Path(intermediate_path)
    output_dir = intermediate_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build config block — type key depends on baseline vs multi-agent
    run_mode = "official" if is_official else "test"
    config_block: dict[str, Any] = {
        "model_key": model_key,
        "model_id": config.model_id,
        "provider": config.provider.value,
        "run_mode": run_mode,
        "samples_per_tier": samples_per_tier,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "max_contract_chars": max_contract_chars,
        "include_negative": include_negative,
    }

    if prompt is not None:
        config_block["baseline_type"] = run_type
        config_block["baseline_label"] = run_label
    else:
        config_block["experiment_type"] = run_type
        config_block["experiment_label"] = run_label

    summary: dict[str, Any] = {
        "run_id": run_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "config": config_block,
    }

    # Add prompt or architecture
    if prompt is not None:
        summary["prompt"] = prompt
    if architecture is not None:
        summary["architecture"] = architecture

    summary["metrics"] = {
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "f2": metrics["f2"],
        "avg_jaccard": metrics["avg_jaccard"],
        "avg_containment": metrics["avg_containment"],
        "avg_span_coverage": metrics["avg_span_coverage"],
        "laziness_rate": metrics["laziness_rate"],
        "tp": metrics["tp"],
        "fp": metrics["fp"],
        "fn": metrics["fn"],
        "tn": metrics["tn"],
    }
    summary["per_tier"] = per_tier

    # Add routing accuracy for M1 runs
    routing_results = [
        r["trace"]["routing_correct"]
        for r in results
        if "trace" in r and r["trace"].get("routing_correct") is not None
    ]
    if routing_results:
        summary["metrics"]["routing_accuracy"] = sum(routing_results) / len(routing_results)
        summary["metrics"]["routing_total"] = len(routing_results)
        summary["metrics"]["routing_correct"] = sum(routing_results)

    # Compact per-sample view
    samples_compact = []
    for r in results:
        entry: dict[str, Any] = {
            "id": r["sample_id"],
            "category": r["category"],
            "tier": r["tier"],
            "classification": r["evaluation"]["classification"],
            "jaccard": r["evaluation"]["jaccard"],
            "grounding_rate": r["evaluation"]["grounding_rate"],
            "num_clauses_predicted": r["output"]["num_clauses"],
            "num_gt_spans": r["ground_truth"]["num_spans"],
            "input_tokens": r["usage"]["input_tokens"],
            "output_tokens": r["usage"]["output_tokens"],
            "latency_s": r["usage"]["latency_s"],
        }
        if "containment" in r["evaluation"]:
            entry["containment"] = r["evaluation"]["containment"]
        if "span_coverage" in r["evaluation"]:
            entry["span_coverage"] = r["evaluation"]["span_coverage"]
        # Include routing info for M1
        if "trace" in r and r["trace"].get("agent_routed_to"):
            entry["agent_routed_to"] = r["trace"]["agent_routed_to"]
            entry["routing_correct"] = r["trace"].get("routing_correct")
        samples_compact.append(entry)
    summary["samples"] = samples_compact
    summary["diagnostics"] = diag_summary
    summary["intermediate_file"] = str(intermediate_path)

    # Save summary
    summary_path = output_dir / f"{run_id}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"Summary saved:      {summary_path}")

    # Save diagnostics
    diagnostics.run_mode = run_mode
    diag_dir = output_dir.parent / "diagnostics"
    diag_dir.mkdir(parents=True, exist_ok=True)
    diag_path = diag_dir / f"{run_id}_diagnostics.json"
    diagnostics.export(diag_path)
    print(f"Diagnostics saved:  {diag_path}")

    # Remind about intermediate
    print(f"Intermediate saved: {intermediate_path}")
    print(f"\nTo inspect a single record:")
    print(f"  head -1 {intermediate_path} | python -m json.tool")

    return summary_path, diag_path
