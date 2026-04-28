#!/usr/bin/env python3
"""Long-format export of all official experiment runs.

Outputs (under experiments/exports/):
  - samples_long.csv             one row per (run, sample), ~150k rows
  - runs_summary.csv             one row per official run
  - samples_qualitative.jsonl    bulky text sidecar (raw_response, gt spans, ...)
  - clm_export.xlsx              workbook: runs_summary + samples_long sheets

Run:
  uv run --with openpyxl python scripts/export_long_format.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path("/Users/trungnguyen/Documents/@tum/study/Thesis/agentic-ai-for-clm")
RESULTS = ROOT / "experiments" / "results"
DIAG = ROOT / "experiments" / "diagnostics"
OUT = ROOT / "experiments" / "exports"
OUT.mkdir(parents=True, exist_ok=True)


def find_canonical_official_runs() -> dict[tuple[str, str], tuple[Path, dict]]:
    """For each (strategy, model_key), pick canonical official run.

    Tie-break: most samples in summary, then latest timestamp.
    """
    by_key: dict[tuple[str, str], tuple[tuple, Path, dict]] = {}
    for p in sorted(RESULTS.glob("*_summary.json")):
        try:
            d = json.load(open(p))
        except Exception as e:
            print(f"  skip {p.name}: {e}")
            continue
        cfg = d.get("config", {}) or {}
        if cfg.get("run_mode") != "official":
            continue
        strategy = (
            cfg.get("baseline_label")
            or cfg.get("experiment_label")
            or "unknown"
        )
        model_key = cfg.get("model_key", "unknown")
        n = len(d.get("samples", []))
        ts = d.get("timestamp", "") or ""
        score = (n, ts)
        key = (strategy, model_key)
        if key not in by_key or score > by_key[key][0]:
            by_key[key] = (score, p, d)
    return {k: (v[1], v[2]) for k, v in by_key.items()}


def stem_for(summary_path: Path) -> str:
    return summary_path.name[: -len("_summary.json")]


def load_diagnostics(stem: str) -> dict | None:
    p = DIAG / f"{stem}_diagnostics.json"
    return json.load(open(p)) if p.exists() else None


def build():
    canonical = find_canonical_official_runs()
    print(f"Found {len(canonical)} canonical official runs")
    for (strategy, model_key) in sorted(canonical):
        print(f"  {strategy:>22}  {model_key}")

    long_rows: list[dict] = []
    runs_rows: list[dict] = []
    qual_path = OUT / "samples_qualitative.jsonl"

    with open(qual_path, "w") as qual_f:
        for (strategy, model_key), (summary_path, summary) in sorted(canonical.items()):
            stem = stem_for(summary_path)
            cfg = summary.get("config", {}) or {}
            run_id = summary.get("run_id", stem)
            timestamp = summary.get("timestamp", "")
            provider = cfg.get("provider", "")
            model_id = cfg.get("model_id", "")
            experiment_code = (
                cfg.get("baseline_type") or cfg.get("experiment_type") or ""
            )

            jsonl_path = RESULTS / f"{stem}_intermediate.jsonl"
            n_jsonl = 0
            if jsonl_path.exists():
                with open(jsonl_path) as f:
                    for line in f:
                        try:
                            rec = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        n_jsonl += 1
                        out = rec.get("output", {}) or {}
                        gt = rec.get("ground_truth", {}) or {}
                        ev = rec.get("evaluation", {}) or {}
                        us = rec.get("usage", {}) or {}
                        tr = rec.get("trace", {}) or {}

                        parsed = out.get("parsed_clauses") or []
                        num_clauses = out.get("num_clauses", len(parsed))
                        raw_lc = (out.get("raw_response") or "").strip().lower()
                        predicted_no_clause = (
                            num_clauses == 0 or "no related clause" in raw_lc
                        )

                        long_rows.append({
                            "run_id": run_id,
                            "model_key": rec.get("model_key", model_key),
                            "model_id": rec.get("model_id", model_id),
                            "provider": provider,
                            "strategy": strategy,
                            "experiment_code": experiment_code,
                            "timestamp": rec.get("timestamp", timestamp),
                            "sample_id": rec.get("sample_id"),
                            "contract_title": rec.get("contract_title"),
                            "contract_chars": rec.get("contract_chars"),
                            "category": rec.get("category"),
                            "tier": rec.get("tier"),
                            "has_clause_gt": gt.get("has_clause"),
                            "num_gt_spans": gt.get("num_spans"),
                            "classification": ev.get("classification"),
                            "jaccard": ev.get("jaccard"),
                            "span_coverage": ev.get("span_coverage"),
                            "containment": ev.get("containment"),
                            "grounding_rate": ev.get("grounding_rate"),
                            "num_clauses_predicted": num_clauses,
                            "predicted_no_clause": predicted_no_clause,
                            "input_tokens": us.get("input_tokens"),
                            "output_tokens": us.get("output_tokens"),
                            "cache_read_tokens": us.get("cache_read_tokens"),
                            "cache_creation_tokens": us.get("cache_creation_tokens"),
                            "total_tokens": (us.get("input_tokens") or 0)
                            + (us.get("output_tokens") or 0),
                            "latency_s": us.get("latency_s"),
                            "agent_routed_to": tr.get("agent_routed_to"),
                            "routing_correct": tr.get("routing_correct"),
                            "num_llm_calls": tr.get("num_llm_calls"),
                            "num_nodes_visited": (
                                len(tr.get("nodes_visited") or [])
                                if tr.get("nodes_visited") is not None
                                else None
                            ),
                            "confidence": out.get("confidence"),
                        })

                        qual_f.write(
                            json.dumps(
                                {
                                    "run_id": run_id,
                                    "sample_id": rec.get("sample_id"),
                                    "category": rec.get("category"),
                                    "tier": rec.get("tier"),
                                    "raw_response": out.get("raw_response"),
                                    "parsed_clauses": parsed,
                                    "reasoning": out.get("reasoning"),
                                    "confidence": out.get("confidence"),
                                    "gt_spans": gt.get("spans"),
                                    "gt_full_text": gt.get("full_text"),
                                    "routing_reasoning": tr.get("routing_reasoning"),
                                    "nodes_visited": tr.get("nodes_visited"),
                                }
                            )
                            + "\n"
                        )
            else:
                print(f"  WARN: missing JSONL for {stem}")

            m = summary.get("metrics", {}) or {}
            pt = summary.get("per_tier", {}) or {}
            diag = load_diagnostics(stem) or {}
            ds = diag.get("summary", {}) or {}

            row = {
                "run_id": run_id,
                "model_key": model_key,
                "model_id": model_id,
                "provider": provider,
                "strategy": strategy,
                "experiment_code": experiment_code,
                "timestamp": timestamp,
                "n_samples_summary": len(summary.get("samples", []) or []),
                "n_samples_jsonl": n_jsonl,
                "duration_seconds": ds.get("duration_seconds"),
                "precision": m.get("precision"),
                "recall": m.get("recall"),
                "f1": m.get("f1"),
                "f2": m.get("f2"),
                "avg_jaccard": m.get("avg_jaccard"),
                "avg_containment": m.get("avg_containment"),
                "avg_span_coverage": m.get("avg_span_coverage"),
                "laziness_rate": m.get("laziness_rate"),
                "tp": m.get("tp"),
                "fp": m.get("fp"),
                "fn": m.get("fn"),
                "tn": m.get("tn"),
                "total_input_tokens": ds.get("total_input_tokens"),
                "total_output_tokens": ds.get("total_output_tokens"),
                "total_tokens": ds.get("total_tokens"),
                "total_cost_usd": ds.get("total_cost_usd"),
                "avg_latency_ms": ds.get("avg_latency_ms"),
            }
            for tier in ("common", "moderate", "rare"):
                t = pt.get(tier, {}) or {}
                row[f"f1_{tier}"] = t.get("f1")
                row[f"f2_{tier}"] = t.get("f2")
                row[f"jaccard_{tier}"] = t.get("avg_jaccard")
                for k in ("tp", "fp", "fn", "tn"):
                    row[f"{k}_{tier}"] = t.get(k)
            if strategy == "multiagent":
                ba = ds.get("by_agent", {}) or {}
                row["num_orchestrator_calls"] = ba.get("orchestrator_router")
                row["num_temporal_renewal_calls"] = ba.get("temporal_renewal")
                row["num_risk_liability_calls"] = ba.get("risk_liability")
                row["num_ip_commercial_calls"] = ba.get("ip_commercial")
            runs_rows.append(row)

    long_df = pd.DataFrame(long_rows)
    runs_df = pd.DataFrame(runs_rows).sort_values(
        ["strategy", "model_key"]
    ).reset_index(drop=True)

    if "routing_correct" in long_df.columns:
        m1 = long_df[long_df["strategy"] == "multiagent"]
        if not m1.empty:
            acc = (
                m1.groupby("run_id")["routing_correct"]
                .mean()
                .rename("routing_accuracy")
                .reset_index()
            )
            runs_df = runs_df.merge(acc, on="run_id", how="left")

    long_csv = OUT / "samples_long.csv"
    runs_csv = OUT / "runs_summary.csv"
    xlsx = OUT / "clm_export.xlsx"

    long_df.to_csv(long_csv, index=False)
    runs_df.to_csv(runs_csv, index=False)

    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        runs_df.to_excel(w, sheet_name="runs_summary", index=False)
        long_df.to_excel(w, sheet_name="samples_long", index=False)

    print()
    print("Wrote:")
    print(f"  {long_csv}   ({len(long_df):,} rows, {len(long_df.columns)} cols)")
    print(f"  {runs_csv}   ({len(runs_df):,} rows, {len(runs_df.columns)} cols)")
    print(f"  {qual_path}  ({len(long_df):,} lines)")
    print(f"  {xlsx}")


if __name__ == "__main__":
    build()
