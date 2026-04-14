# Impact of Data Selection on Experiment Results

## Context

During baseline calibration (B1 zero-shot, gemini-2.5-flash), we observed a major shift in metrics after changing how positive and negative samples are selected. This document explains the cause and implications.

## Before: `include_negative` (boolean)

The original sampling logic used a boolean flag `include_negative=True`. When enabled, it applied a **fixed heuristic**:

- Positive samples: up to `samples_per_tier` (e.g., 10)
- Negative samples: up to `samples_per_tier // 2` (e.g., 5)

This produced a **~67% positive / 33% negative** split per tier — heavily biased toward positive samples compared to CUAD's natural distribution.

## After: `neg_ratio` (float, 0.0–1.0)

The new sampling logic uses a configurable ratio to split `samples_per_tier` between positive and negative samples:

```
n_neg = round(samples_per_tier * neg_ratio)
n_pos = samples_per_tier - n_neg
```

With `neg_ratio=0.7` and `samples_per_tier=10`:

- Positive samples: 3 per tier
- Negative samples: 7 per tier

This produces a **30% positive / 70% negative** split — matching CUAD's natural label distribution (30/70 as reported in the dataset statistics).

## Sampling comparison

| Setting | Positive per tier | Negative per tier | Positive ratio | Matches CUAD? |
|---------|:-:|:-:|:-:|:-:|
| `include_negative=True` (old) | 10 | 5 | ~67% | No |
| `neg_ratio=0.7` (new) | 3 | 7 | 30% | Yes |

## Observed metric shift

Both runs: B1 (zero-shot), gemini-2.5-flash, `samples_per_tier=10`, `max_contract_chars=100,000`.

| Metric | Old (Mar 17, ~67% pos) | New (Apr 13, 30% pos) | Change |
|--------|:-:|:-:|:-:|
| F1 | 0.813 | 0.483 | -0.330 |
| F2 | 0.844 | 0.625 | -0.219 |
| Precision | 0.765 | 0.350 | -0.415 |
| Recall | 0.867 | 0.778 | -0.089 |
| Jaccard | 0.314 | 0.420 | +0.106 |

## Why each metric moved

### Precision collapsed (0.765 → 0.350)

With 2x more negative samples, there are far more opportunities for **false positives** — the model extracts a clause when no relevant clause exists. Under the old positive-heavy sampling, this weakness was hidden because negative samples were underrepresented.

### Recall barely changed (0.867 → 0.778)

The model still finds clauses when they actually exist. The slight drop is likely small-sample variance from having fewer positive samples per tier (3 instead of 10).

### F1 dropped sharply (0.813 → 0.483)

F1 weights precision and recall equally. The precision collapse drove F1 down.

### F2 dropped less (0.844 → 0.625)

F2 weights recall more heavily than precision (5P·R / 4P+R), so it absorbed the precision drop better.

### Jaccard improved (0.314 → 0.420)

For the positive samples where clauses are correctly found, the span overlap actually improved. This is likely small-sample variance — with only 9 positive samples (3 per tier) vs. 30 before (10 per tier), individual samples have more influence on the average.

## Implications

### 1. The old sampling was flattering

Oversampling positives masked the model's tendency to **hallucinate clauses on negative samples**. A 67% positive evaluation set does not represent real-world contract review, where most clause-type checks come back empty.

### 2. The real weakness: over-extraction, not laziness

Previous work (including ContractEval) focused on the "laziness problem" — models saying "No related clause" when clauses exist. The new results reveal the **opposite problem**: models extracting text even when no relevant clause is present. Both failure modes matter, and the sampling ratio determines which one dominates the metrics.

### 3. CUAD's natural 30/70 split is the right benchmark

The 70% negative rate reflects reality: in contract review, most clause-type queries for any given contract return empty. Evaluating at this ratio gives a more honest picture of model performance and better predicts deployment behavior.

### 4. Small sample sizes amplify the effect

With `samples_per_tier=10`, the new ratio yields only 3 positive samples per tier (9 total). Metrics at this scale are noisy. Official runs with `samples_per_tier=200` will produce 60 positive + 140 negative per tier (600 total), giving much more stable estimates while maintaining the natural distribution.

## Recommendation

All official experiment runs should use `neg_ratio=0.7` to match CUAD's natural distribution. This ensures:

- Fair comparison across models (same pos/neg ratio)
- Realistic precision estimates that reflect deployment conditions
- Both laziness (FN on positives) and over-extraction (FP on negatives) are properly measured

For diagnostic runs, `neg_ratio=0.0` (positive-only) can still be useful to isolate extraction quality without the FP noise.
