"""Shared extraction loop for baseline and multi-agent experiments.

Both notebook 03 (baselines) and notebook 04 (multi-agent) share identical
evaluation, record building, JSONL persistence, and resume logic.  The only
difference is *how* extraction is called.  Notebooks supply a thin
``extract_fn`` closure; this module handles everything else.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

from tqdm.auto import tqdm

from src.evaluation.metrics import (
    compute_grounding_rate,
    compute_jaccard,
    span_overlap,
)


@dataclass
class ExtractionOutput:
    """Return type for the ``extract_fn`` closure passed to :func:`run_extraction`.

    Notebooks build this from their model-specific extraction logic.
    """

    extracted_clauses: list[str] = field(default_factory=list)
    raw_response: str = ""
    reasoning: str | None = None
    confidence: float | None = None
    system_prompt: str | None = None
    user_message_length: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    trace_nodes: list[str] | None = None  # M1 only


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _evaluate_sample(sample: Any, output: ExtractionOutput) -> dict[str, Any]:
    """Classify as TP/FP/FN/TN and compute Jaccard + grounding."""
    predicted_text = " ".join(output.extracted_clauses)
    has_prediction = len(output.extracted_clauses) > 0

    if sample.has_clause:
        if has_prediction:
            covers = any(
                span_overlap(predicted_text, gt)
                for gt in sample.ground_truth_spans
            )
            classification = "TP" if covers else "FN"
        else:
            classification = "FN"
    else:
        classification = "FP" if has_prediction else "TN"

    jacc = (
        compute_jaccard(predicted_text, sample.ground_truth)
        if sample.has_clause and has_prediction
        else (1.0 if not sample.has_clause and not has_prediction else 0.0)
    )
    grounding = (
        compute_grounding_rate(output.extracted_clauses, sample.contract_text)
        if has_prediction
        else 1.0
    )

    return {
        "classification": classification,
        "jaccard": jacc,
        "grounding_rate": grounding,
    }


def _build_record(
    sample: Any,
    output: ExtractionOutput,
    evaluation: dict[str, Any],
    elapsed: float,
    *,
    run_id: str,
    model_key: str,
    model_id: str,
    run_type: str,
    run_label: str,
    run_type_key: str,
    run_mode: str,
) -> dict[str, Any]:
    """Build the full JSONL record for one sample."""
    # Type key: baseline_type/baseline_label vs experiment_type/experiment_label
    type_key = f"{run_type_key}_type"
    label_key = f"{run_type_key}_label"

    record: dict[str, Any] = {
        "sample_id": sample.id,
        "run_id": run_id,
        "run_mode": run_mode,
        "timestamp": datetime.datetime.now().isoformat(),
        "model_key": model_key,
        "model_id": model_id,
        type_key: run_type,
        label_key: run_label,
        "category": sample.category,
        "tier": sample.tier,
        "contract_title": sample.contract_title,
        "contract_chars": len(sample.contract_text),
        "input": {
            "system_prompt": output.system_prompt,
            "user_message_length": output.user_message_length,
            "question": sample.question,
        },
        "output": {
            "raw_response": output.raw_response,
            "parsed_clauses": output.extracted_clauses,
            "num_clauses": len(output.extracted_clauses),
            "reasoning": output.reasoning,
            "confidence": output.confidence,
        },
        "ground_truth": {
            "has_clause": sample.has_clause,
            "spans": sample.ground_truth_spans,
            "full_text": sample.ground_truth,
            "num_spans": sample.num_spans,
        },
        "evaluation": evaluation,
        "usage": {
            "input_tokens": output.input_tokens,
            "output_tokens": output.output_tokens,
            "cache_read_tokens": output.cache_read_tokens,
            "cache_creation_tokens": output.cache_creation_tokens,
            "latency_s": round(elapsed, 2),
        },
    }

    # Add trace block only when trace_nodes is set (M1)
    if output.trace_nodes is not None:
        record["trace"] = {
            "nodes_visited": output.trace_nodes,
            "num_llm_calls": len(output.trace_nodes),
        }

    return record


def _build_error_record(
    sample: Any,
    error: Exception,
    elapsed: float,
    *,
    run_id: str,
    model_key: str,
    run_type: str,
    run_type_key: str,
    run_mode: str,
) -> dict[str, Any]:
    """Build a minimal error record for JSONL."""
    type_key = f"{run_type_key}_type"
    return {
        "sample_id": sample.id,
        "run_id": run_id,
        "run_mode": run_mode,
        "timestamp": datetime.datetime.now().isoformat(),
        "status": "error",
        "error": str(error),
        "error_type": type(error).__name__,
        "model_key": model_key,
        type_key: run_type,
        "category": sample.category,
        "tier": sample.tier,
        "contract_title": sample.contract_title,
        "latency_s": round(elapsed, 2),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_extraction(
    samples: list[Any],
    extract_fn: Callable[[Any], Awaitable[ExtractionOutput]],
    *,
    run_id: str,
    model_key: str,
    model_id: str,
    run_type: str,
    run_label: str,
    run_type_key: str,
    intermediate_path: Path | str,
    concurrency: int = 1,
    is_official: bool = False,
) -> tuple[list[dict], list[dict]]:
    """Run the extraction loop with resume, evaluation, JSONL persistence.

    Args:
        samples: List of CUAD sample objects.
        extract_fn: Async callable ``sample -> ExtractionOutput``.  Encapsulates
            all model-specific logic (prompt building, API call, parsing).
        run_id: Unique run identifier.
        model_key: Model registry key.
        model_id: Full model identifier string.
        run_type: Short label (``"B1"``, ``"M1"``, etc.).
        run_label: Descriptive label (``"zero_shot"``, ``"multiagent"``, etc.).
        run_type_key: ``"baseline"`` or ``"experiment"`` — controls which keys
            appear in the JSONL record (``baseline_type`` vs ``experiment_type``).
        intermediate_path: Path to the JSONL file for crash-safe persistence.
        concurrency: Maximum number of parallel API calls (Semaphore width).
        is_official: If True, marks the run as ``"official"``; otherwise ``"test"``.

    Returns:
        ``(results, failures)`` — lists of successful records and error records.
    """
    intermediate_path = Path(intermediate_path)
    run_mode = "official" if is_official else "test"

    # ── Resume: load existing completed samples (skip error records) ──
    resumed_results: list[dict] = []
    completed_ids: set[str] = set()
    if intermediate_path.exists():
        with open(intermediate_path) as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    if rec.get("status") == "error":
                        continue  # Will retry
                    completed_ids.add(rec["sample_id"])
                    resumed_results.append(rec)
        if completed_ids:
            print(f"Resuming:     {len(completed_ids)} samples already completed")

    pending = [s for s in samples if s.id not in completed_ids]
    print(f"Pending: {len(pending)} samples ({len(completed_ids)} already done)\n")

    if not pending:
        return resumed_results, []

    # ── Concurrent extraction ──
    semaphore = asyncio.Semaphore(concurrency)
    jsonl_lock = asyncio.Lock()
    new_results: list[dict] = []
    failures: list[dict] = []

    async def _process(sample: Any, pbar: tqdm) -> None:
        async with semaphore:
            t0 = time.time()
            try:
                output = await extract_fn(sample)
                elapsed = time.time() - t0

                evaluation = _evaluate_sample(sample, output)
                record = _build_record(
                    sample,
                    output,
                    evaluation,
                    elapsed,
                    run_id=run_id,
                    model_key=model_key,
                    model_id=model_id,
                    run_type=run_type,
                    run_label=run_label,
                    run_type_key=run_type_key,
                    run_mode=run_mode,
                )

                async with jsonl_lock:
                    with open(intermediate_path, "a") as f:
                        f.write(json.dumps(record, default=str) + "\n")

                new_results.append(record)

                cls = evaluation["classification"]
                jacc = evaluation["jaccard"]
                pbar.update(1)
                pbar.set_postfix_str(
                    f"{sample.category[:20]} -> {cls} J={jacc:.3f}"
                )

            except Exception as e:
                elapsed = time.time() - t0
                error_record = _build_error_record(
                    sample,
                    e,
                    elapsed,
                    run_id=run_id,
                    model_key=model_key,
                    run_type=run_type,
                    run_type_key=run_type_key,
                    run_mode=run_mode,
                )
                async with jsonl_lock:
                    with open(intermediate_path, "a") as f:
                        f.write(json.dumps(error_record, default=str) + "\n")

                failures.append(error_record)
                pbar.update(1)
                pbar.set_postfix_str(f"{sample.category[:20]} -> ERROR")

    start_time = time.time()
    with tqdm(total=len(pending), desc=f"{run_type} {model_key}") as pbar:
        tasks = [_process(s, pbar) for s in pending]
        await asyncio.gather(*tasks)

    total_time = time.time() - start_time
    print(
        f"\nCompleted: {len(new_results)} success, {len(failures)} failed "
        f"({len(completed_ids)} resumed)"
    )
    print(f"Intermediate saved to: {intermediate_path}")
    print(f"Total wall time: {total_time:.1f}s")

    if failures:
        print(f"\nFailed samples ({len(failures)}):")
        for r in failures:
            print(f"  {r['category']} ({r['tier']}) — {r['error_type']}: {r['error']}")

    all_results = resumed_results + new_results
    return all_results, failures
