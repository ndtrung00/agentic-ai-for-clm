# F1/Jaccard Discrepancy Diagnosis

**Date:** 2026-03-02 15:00 UTC
**Author:** Claude Code (audit)
**Scope:** `src/experiments/runner.py`, `src/evaluation/metrics.py`, `src/data/cuad_loader.py`

---

## Summary

Experiments show F1/F2 scores of 0.8--0.9 but Jaccard similarity of 0.2--0.35. This 2--4x gap is caused by three bugs in the evaluation pipeline that inflate the TP count while Jaccard measures something fundamentally different from what the TP logic checks.

**347 out of 688 TP samples (50%) have Jaccard < 0.3.** The F1 score is unreliable as currently computed.

---

## Bug 1: TP checks ALL spans, Jaccard uses ONLY the first span

### Location

`src/experiments/runner.py` lines 52--84, function `_evaluate_sample()`

### Code

```python
# TP classification — matches ANY span from ground_truth_spans (ALL spans)
covers = any(
    span_overlap(predicted_text, gt)
    for gt in sample.ground_truth_spans   # ← checks all spans
)
classification = "TP" if covers else "FN"

# Jaccard — computed against sample.ground_truth (FIRST span only)
jacc = compute_jaccard(predicted_text, sample.ground_truth)  # ← first span
```

### Data structure

From `src/data/cuad_loader.py`:

```python
ground_truth = answer_texts[0] if answer_texts else ""   # first span only
ground_truth_spans = answer_texts                         # all spans
```

Confirmed: `sample.ground_truth == sample.ground_truth_spans[0]` in all checked samples.

### Mechanism

When a ground truth has multiple labeled spans (e.g., "Parties" with 4 spans), the model's prediction may match span[2] (triggering TP) but Jaccard is measured against span[0] (a completely different string). The two metrics decouple.

### Example: Parties category (4 spans)

- **GT spans:** `["WLI", "Wireless Links Inc", "Power2Ship", ...]`
- **GT first span (for Jaccard):** `"WLI"`
- **Prediction:** `"This Agreement is made and entered into this 7th day of April, 2003... by and between Wireless Links Inc..."`
- **TP check:** `span_overlap(prediction, "Wireless Links Inc")` → True (substring found) → **TP**
- **Jaccard:** `compute_jaccard(prediction, "WLI")` → token `"wli"` not found in prediction tokens → **Jaccard = 0.0**

### Scale

| num_spans | Total TPs | Jaccard < 0.3 | % affected |
|-----------|-----------|---------------|------------|
| 1         | 413       | 161           | 39%        |
| 2         | 140       | 74            | 53%        |
| 3         | 52        | 39            | 75%        |
| 4         | 43        | 37            | 86%        |
| 5+        | 40        | 36            | 90%        |

Multi-span samples are almost guaranteed to have misleading Jaccard.

---

## Bug 2: Substring matching (TP) vs token matching (Jaccard)

### Location

- `src/evaluation/metrics.py` line 236: `span_overlap()` — substring-based
- `src/evaluation/metrics.py` line 122: `compute_jaccard()` — token-based

### Code

```python
# span_overlap: substring matching (punctuation-immune)
def span_overlap(pred_span, truth_span):
    pred_normalized = " ".join(pred_span.split()).lower()
    truth_normalized = " ".join(truth_span.split()).lower()
    return truth_normalized in pred_normalized

# compute_jaccard: token set matching (punctuation-sensitive)
def compute_jaccard(prediction, ground_truth):
    pred_tokens = set(prediction.lower().split())
    truth_tokens = set(ground_truth.lower().split())
    intersection = pred_tokens & truth_tokens
    union = pred_tokens | truth_tokens
    return len(intersection) / len(union)
```

### Mechanism

`span_overlap` checks if the truth string appears as a contiguous substring in the prediction. Punctuation around words doesn't matter — `"escrow agreement"` is found within `'is "ESCROW AGREEMENT".'`.

`compute_jaccard` splits on whitespace and compares token sets. Punctuation sticks to tokens — `'"escrow'` ≠ `'escrow'`, `'agreement".'` ≠ `'agreement'`.

### Example: Document Name

- **GT:** `ESCROW AGREEMENT`
- **Prediction:** `The name of the contract is "ESCROW AGREEMENT".`
- **span_overlap:** `"escrow agreement"` found in normalized prediction → **TP**
- **Jaccard tokens:**
  - truth: `{"escrow", "agreement"}`
  - pred: `{"the", "name", "of", "contract", "is", '"escrow', 'agreement".'}`
  - intersection: **empty** (punctuation mismatch)
  - **Jaccard = 0.0**

### Impact

This affects ALL samples where the model wraps extracted text in quotes, parentheses, or adds trailing punctuation — a very common LLM behavior pattern.

---

## Bug 3: Over-extraction penalized by Jaccard but invisible to TP

### Mechanism

When a model extracts a broad clause containing the labeled span, `span_overlap` correctly returns True (the span IS covered). But Jaccard penalizes the extra tokens heavily because `|union|` grows while `|intersection|` stays small.

### Example: Effective Date

- **GT:** `9/24/2018` (1 token)
- **Prediction:** `THIS MASTER SERVICES AGREEMENT ("Agreement"), dated as of 09/24/2018 (the "Effective Date"), is between Clear Capital...` (20+ tokens)
- **span_overlap:** `"9/24/2018"` is substring of `"09/24/2018"` → **TP**
- **Jaccard:** 1 matching token / 20+ total tokens → **Jaccard ≈ 0.0**

### Note

This is arguably correct model behavior — extracting the full sentence containing the date provides better context. But the Jaccard metric treats it as a near-failure. This is a metric design issue, not a model failure.

---

## Evaluation Flow (end to end)

```
Model output
    │
    ▼
pipeline.py: extract_fn(sample) → ExtractionOutput
    │
    ▼
runner.py: _evaluate_sample(sample, output)
    ├── Join clauses: predicted_text = " ".join(output.extracted_clauses)
    ├── TP/FN check: any(span_overlap(predicted_text, gt) for gt in sample.ground_truth_spans)
    ├── Jaccard: compute_jaccard(predicted_text, sample.ground_truth)  ← BUG: first span only
    └── Grounding: compute_grounding_rate(output.extracted_clauses, sample.contract_text)
    │
    ▼
results.py: compute_aggregate_metrics(results)
    ├── Counts TP/FP/FN/TN from classification strings
    ├── F1 = 2*P*R / (P+R)
    ├── F2 = 5*P*R / (4P+R)
    └── avg_jaccard = mean of per-sample Jaccard scores (positive samples only)
```

**Key:** F1 is derived from TP/FP/FN counts. Jaccard is a completely separate token-overlap metric. They are computed against different references and with different matching semantics. This explains the discrepancy.

---

## What ContractEval actually specifies

From the ContractEval paper (Liu et al., 2025):

- **TP:** label is not empty AND model prediction **fully covers** the labeled span
- **TN:** label is empty AND model correctly predicts "no related clause"
- **FP:** label is empty BUT model incorrectly predicts a non-empty clause
- **FN:** label is not empty BUT model outputs "no related clause" OR **fails to fully cover** the label span

"Fully covers" means the ground truth text appears as a substring within the prediction. The `span_overlap()` function implements this correctly.

ContractEval uses Jaccard as a **secondary quality metric** measuring extraction precision, not as part of the TP/FP/FN decision.

**Ambiguity:** ContractEval says "labeled span" (singular). CUAD samples can have multiple answer spans per question. Current code treats ANY span match as TP — this may or may not match ContractEval's intent.

---

## Sample selection analysis

Current setup (from notebook config):

- `SAMPLES_PER_TIER = 5` → 5 positive + ~2 negative per tier
- 3 tiers (common/moderate/rare) × 7 samples = **21 total**
- Stratified by tier, random within tier, `seed=42`
- Draws from all 41 CUAD categories (not a subset)

With only 5 positive samples per tier, most of the 41 categories are not represented in any given run. This is intentional for calibration (small fast runs) but the official runs should use `SAMPLES_PER_TIER = 200` for statistical power.

---

## Concrete data: 7 representative TP + low Jaccard examples

| Model | Category | Tier | Spans | Jaccard | Grounding | Pattern |
|-------|----------|------|-------|---------|-----------|---------|
| gpt-4.1-mini | Parties | common | 4 | 0.0000 | 1.00 | Matched span[1+], Jaccard vs span[0] |
| gpt-4.1-mini | Effective Date | common | 1 | 0.0000 | 1.00 | Over-extraction (full clause for a date) |
| gpt-4.1-mini | Document Name | common | 1 | 0.0000 | 0.00 | Punctuation mismatch (`"ESCROW` ≠ `ESCROW`) |
| gpt-4.1-mini | Agreement Date | common | 1 | 0.0112 | 1.00 | Over-extraction (6 clauses for one date) |
| gpt-4.1-mini | Minimum Commitment | rare | 4 | 0.0155 | 0.00 | Multi-span, partial coverage |
| gpt-4.1-mini | Revenue/Profit Sharing | rare | 2 | 0.0361 | 0.00 | Ungrounded paraphrase |
| gpt-4.1-mini | Insurance | moderate | 3 | 0.0444 | 1.00 | Multi-span, partial coverage |

---

## Recommended fixes

### Fix 1: Compute Jaccard against matched span(s), not first span

```python
# Current (broken)
jacc = compute_jaccard(predicted_text, sample.ground_truth)

# Fix: use all spans, or the best-matching span
jacc = max(
    compute_jaccard(predicted_text, gt)
    for gt in sample.ground_truth_spans
) if sample.ground_truth_spans else 0.0
```

### Fix 2: Add punctuation normalization to Jaccard

```python
import re

def _normalize_tokens(text: str) -> set[str]:
    """Normalize text to token set: lowercase, strip punctuation."""
    text = re.sub(r'[^\w\s]', '', text.lower())
    return set(text.split())

def compute_jaccard(prediction: str, ground_truth: str) -> float:
    pred_tokens = _normalize_tokens(prediction)
    truth_tokens = _normalize_tokens(ground_truth)
    if not pred_tokens | truth_tokens:
        return 0.0
    return len(pred_tokens & truth_tokens) / len(pred_tokens | truth_tokens)
```

### Fix 3: Add a sanity check flag

In `compute_aggregate_metrics()`, add a warning when F1 and Jaccard diverge:

```python
if metrics["f1"] > 0.8 and metrics["avg_jaccard"] < 0.4:
    metrics["warning"] = "F1/Jaccard divergence detected — review TP classification"
```

### Fix 4: Add span-level coverage metric

Track what fraction of ground truth spans the prediction actually covers:

```python
def compute_span_coverage(predicted_text: str, truth_spans: list[str]) -> float:
    """Fraction of ground truth spans covered by prediction."""
    if not truth_spans:
        return 0.0
    covered = sum(1 for gt in truth_spans if span_overlap(predicted_text, gt))
    return covered / len(truth_spans)
```

### Fix 5 (optional): SemEval-style match tiers

Add structured match levels for richer analysis:

- **Strict:** prediction tokens == ground truth tokens (exact match)
- **Exact:** prediction fully covers ground truth AND Jaccard > 0.5
- **Partial:** prediction covers ground truth (current TP logic)
- **Type:** correct TP/TN classification regardless of span quality

---

## Impact on thesis

- **F1/F2 scores are inflated** but not wrong per ContractEval definition — TP classification follows the spec
- **Jaccard is the honest metric** for extraction quality, but it's computed against the wrong reference (Bug 1)
- After fixing Jaccard computation, the gap should narrow significantly
- Multi-agent (M1) may show advantage in Jaccard if specialists learn category-specific extraction granularity
- Recommend reporting **both** F1 and Jaccard prominently, with span coverage as a supplementary metric

---

## Files involved

| File | Lines | Role |
|------|-------|------|
| `src/experiments/runner.py` | 52--84 | `_evaluate_sample()` — **active classification logic (bugs here)** |
| `src/evaluation/metrics.py` | 236--256 | `span_overlap()` — substring matching (correct) |
| `src/evaluation/metrics.py` | 122--148 | `compute_jaccard()` — token matching (needs punctuation fix) |
| `src/evaluation/metrics.py` | 259--308 | `evaluate_single()` — stricter version (unused in pipeline) |
| `src/experiments/results.py` | 24--71 | `compute_aggregate_metrics()` — aggregates TP/FP/FN/TN counts |
| `src/data/cuad_loader.py` | 95--116 | `CUADSample` — `ground_truth` vs `ground_truth_spans` |
