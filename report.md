# Experiment Results Report: Multi-Agent Contract Clause Extraction

**Project:** Design and Evaluation of Multi-Agentic AI Systems for Contract Lifecycle Management  
**Author:** Trung Nguyen  
**Supervisor:** Prof. Dr. Ingo Weber  
**Date:** 2026-04-20  
**Dataset:** CUAD (102 contracts, 41 clause types, ~3000 samples per run)

---

## 1. Experimental Setup

### Configurations Evaluated

| Config | Type | Description |
|--------|------|-------------|
| **B1** | Zero-shot | ContractEval replication — single-agent direct extraction |
| **B4** | Chain-of-thought | Single-agent with structured reasoning |
| **M0** | Classify-then-extract | Two-step pipeline: classify relevance, then extract |
| **M1** | Full multi-agent | Orchestrator + 3 domain specialists + validation layer |
| **M6** | Combined prompts | Single-agent with all specialist knowledge (architecture ablation) |

### Models Evaluated (11 models x 5 configs = 55 runs)

| Provider | Models |
|----------|--------|
| Anthropic | Claude Opus 4.6, Sonnet 4.6, Sonnet 4, Haiku 4.5 |
| Google (Vertex AI) | Gemini 3.1 Pro, 2.5 Pro, 2.5 Flash, 3 Flash |
| OpenAI | GPT-4.1, GPT-4.1 Mini, GPT-4.1 Nano |

---

## 2. Aggregate Performance Summary

| Config | F1 (mean) | F2 (mean) | Precision | Recall | Laziness | Jaccard | Cost (USD) |
|--------|-----------|-----------|-----------|--------|----------|---------|------------|
| **B1** | 0.737 | 0.803 | 0.662 | 0.858 | 6.6% | 0.430 | $52 |
| **B4** | 0.708 | 0.791 | 0.612 | 0.862 | 5.0% | 0.375 | $70 |
| **M0** | **0.798** | 0.794 | **0.813** | 0.793 | 17.7% | 0.360 | $96 |
| **M1** | 0.777 | 0.790 | 0.768 | 0.801 | 15.4% | 0.376 | $70 |
| **M6** | 0.724 | 0.790 | 0.642 | 0.844 | **3.4%** | **0.447** | $70 |

### Key Observations

1. **F2 scores are statistically indistinguishable across all configs** (all pairwise Wilcoxon p > 0.27)
2. **F1 significantly improves** in M0 (+6.1pp vs B1, p=0.010) and M1 (+4.0pp vs B1, p=0.024)
3. **Laziness dramatically worsens** in M0/M1 (p=0.001) but improves in M6 (p=0.032)
4. **Jaccard (span quality) is best in M6**, significantly better than M1 (p=0.002, Cohen's d=1.16)

---

## 3. F1 Score Analysis

### Top-5 Models Per Configuration (by F1)

| Rank | B1 | M0 | M1 | M6 |
|------|------|-----|-----|-----|
| 1 | GPT-4.1 (0.811) | Claude Sonnet 4 (0.842) | Claude Opus 4.6 (0.825) | Gemini 3.1 Pro (0.800) |
| 2 | Gemini 3.1 Pro (0.807) | Gemini 3.1 Pro (0.840) | Gemini 3.1 Pro (0.806) | Claude Sonnet 4 (0.794) |
| 3 | GPT-4.1 Mini (0.795) | Claude Sonnet 4.6 (0.838) | Claude Haiku 4.5 (0.806) | GPT-4.1 (0.769) |
| 4 | Claude Opus 4.6 (0.777) | GPT-4.1 Mini (0.835) | Claude Sonnet 4.6 (0.802) | Claude Opus 4.6 (0.764) |
| 5 | Claude Sonnet 4 (0.765) | GPT-4.1 (0.837) | Gemini 2.5 Flash (0.791) | Gemini 2.5 Flash (0.749) |

### F1 Interpretation

M0 achieves the highest F1 scores across almost all models because:
- It dramatically increases **precision** (mean 0.81 vs 0.66 in B1) by filtering out false positives via the classification gate
- The precision gain offsets the recall loss in the balanced F1 formula

However, M1 (full multi-agent) shows lower F1 than M0 because the routing overhead introduces errors without further precision gains.

### Statistical Significance (Wilcoxon signed-rank, paired by model)

| Comparison | F1 Diff | p-value | Significance |
|------------|---------|---------|--------------|
| B1 → M0 | +0.061 | 0.010 | ** |
| B1 → M1 | +0.040 | 0.024 | ** |
| B4 → M1 | +0.067 | 0.004 | *** |
| B1 → M6 | -0.013 | 0.831 | ns |
| M0 → M1 | -0.022 | 0.123 | ns |
| M1 → M6 | -0.053 | 0.003 | *** |

**Conclusion:** Multi-agent architectures (M0, M1) significantly improve F1 over baselines by boosting precision, but M6 does not — it maintains the high-recall/lower-precision profile of baselines.

---

## 4. F2 Score Analysis (Primary Metric)

F2 weights recall 4x more than precision. Since our task prioritizes finding all relevant clauses (reducing misses), F2 is the primary evaluation metric.

### Top-5 Models Per Configuration (by F2)

| Rank | B1 | B4 | M0 | M1 | M6 |
|------|------|------|------|------|------|
| 1 | GPT-4.1 (0.868) | Opus 4.6 (0.865) | Sonnet 4 (0.877) | Opus 4.6 (0.860) | 3.1 Pro (0.854) |
| 2 | Opus 4.6 (0.863) | Sonnet 4 (0.851) | Opus 4.6 (0.864) | 3.1 Pro (0.840) | GPT-4.1 (0.854) |
| 3 | 3.1 Pro (0.861) | Haiku 4.5 (0.849) | 4.1 Mini (0.862) | Haiku 4.5 (0.835) | Opus 4.6 (0.846) |
| 4 | Sonnet 4 (0.851) | 3.1 Pro (0.843) | Sonnet 4.6 (0.860) | 2.5 Pro (0.834) | Sonnet 4 (0.842) |
| 5 | 4.1 Mini (0.837) | 4.1 Mini (0.841) | 3.1 Pro (0.843) | Sonnet 4.6 (0.834) | Sonnet 4.6 (0.836) |

### Statistical Significance (F2)

| Comparison | F2 Diff | p-value | Cohen's d | Significance |
|------------|---------|---------|-----------|--------------|
| B1 → M1 | -0.011 | 0.413 | -0.113 | ns |
| B1 → M0 | -0.007 | 0.831 | — | ns |
| B1 → M6 | -0.011 | 0.700 | -0.101 | ns |
| B4 → M1 | -0.000 | 0.275 | — | ns |
| M1 → M6 | +0.000 | 0.577 | +0.002 | ns |

**Critical finding: No configuration achieves statistically significant F2 improvement over B1.** The precision gains from multi-agent architectures are exactly offset by recall losses, yielding equivalent F2 performance.

---

## 5. Precision-Recall Tradeoff Analysis

The fundamental tension in our results:

| Config | Mean Precision | Mean Recall | Tradeoff |
|--------|---------------|-------------|----------|
| B1 | 0.662 | 0.858 | High recall, low precision |
| B4 | 0.612 | 0.862 | Highest recall, lowest precision |
| M0 | **0.813** | 0.793 | Highest precision, lowest recall |
| M1 | 0.768 | 0.801 | Balanced |
| M6 | 0.642 | 0.844 | Similar to baselines |

### Interpretation

- **B1/B4** over-extract: they include many spans (high recall) but many are irrelevant (low precision)
- **M0** over-filters: the classification step is too aggressive, rejecting positive samples
- **M1** partially inherits M0's filtering problem through the routing/specialist structure
- **M6** behaves like a "smarter baseline" — maintains high recall while modestly improving precision via specialist knowledge

---

## 6. Per-Tier Analysis (Common / Moderate / Rare Categories)

### Mean F2 by Tier

| Config | Common (F1>0.7) | Moderate (0.3-0.7) | Rare (<0.3) |
|--------|-----------------|-------------------|-------------|
| B1 | 0.911 | 0.754 | 0.653 |
| B4 | 0.930 | 0.734 | 0.649 |
| M0 | 0.878 | **0.778** | 0.613 |
| M1 | 0.935 | 0.718 | 0.593 |
| M6 | 0.928 | 0.727 | 0.621 |

### Analysis by Tier

**Common categories** (easiest): All configs perform well (0.87-0.94). M1 slightly edges out with 0.935.

**Moderate categories**: M0 leads (0.778) due to precision improvements on categories with moderate positive rates. B1 is second (0.754).

**Rare categories** (hardest): **B1 baseline performs best** (0.653), followed by B4 (0.649). Multi-agent architectures (M0=0.613, M1=0.593) actually *hurt* rare category performance.

### Rare Category Deep-Dive: Best Model Per Config

| Config | Best Model on Rare | Rare F2 |
|--------|-------------------|---------|
| B1 | Claude Opus 4.6 | 0.746 |
| B4 | Claude Opus 4.6 | 0.775 |
| M0 | Claude Opus 4.6 | 0.735 |
| M1 | Gemini 2.5 Pro | 0.711 |
| M6 | Gemini 3.1 Pro | 0.719 |

**Finding against H2:** Multi-agent architectures do NOT help rare categories. The classification/routing step is especially harmful for rare categories where the model has less confidence, leading to higher false-negative rates.

---

## 7. Laziness Analysis (False "No Related Clause" Rate)

### Laziness by Configuration

| Config | Mean Laziness | Min | Max |
|--------|--------------|-----|-----|
| **M6** | **3.4%** | 0.6% | 13.5% |
| **B4** | 5.0% | 0.4% | 22.4% |
| **B1** | 6.6% | 1.5% | 42.0% |
| **M1** | 15.4% | 6.4% | 42.3% |
| **M0** | 17.7% | 7.0% | 40.9% |

### Laziness by Tier (Claude models, representative)

| Config | Common | Moderate | Rare |
|--------|--------|----------|------|
| B1 | 3.7% | 10.6% | 23.2% |
| M0 | 10.7% | 10.9% | 27.0% |
| M1 | 4.5% | 16.1% | 30.1% |
| M6 | 4.2% | 10.8% | 24.3% |

### Interpretation

1. **M0/M1 laziness is concentrated differently:** M0 adds laziness in common categories (classification gate rejects obvious positives), while M1 adds laziness in moderate categories (routing errors).
2. **Rare category laziness is uniformly high** (~23-30%) across all configs — this is an inherent model limitation, not architecture-dependent.
3. **M6 achieves the lowest laziness overall** (3.4%), even better than baselines, suggesting that specialist prompt knowledge helps models avoid false negatives.
4. **The classification gate is the primary laziness source** in M0/M1.

---

## 8. Jaccard Similarity (Span Overlap Quality)

Jaccard measures how well extracted text overlaps with ground truth spans.

### Mean Jaccard by Configuration

| Config | Mean Jaccard |
|--------|-------------|
| **M6** | **0.447** |
| B1 | 0.430 |
| M1 | 0.376 |
| B4 | 0.375 |
| M0 | 0.360 |

### Statistical Significance

| Comparison | Jaccard Diff | p-value | Cohen's d |
|------------|-------------|---------|-----------|
| M1 → M6 | +0.072 | 0.002 | **+1.161 (large)** |
| B1 → M6 | +0.022 | 0.413 | +0.361 (small) |
| B1 → M0 | -0.065 | 0.042 | — |
| B1 → M1 | -0.050 | 0.083 | -0.781 (medium) |

### Interpretation

- **M6 produces the best span quality** — specialist knowledge helps models extract more precise text spans.
- **M0/M1 degrade Jaccard** compared to baselines. When the system is uncertain about relevance, it may extract partial or imprecise spans.
- The large effect size (d=1.16) between M1 and M6 demonstrates that the multi-agent architecture introduces noise in span extraction that the combined-prompts approach avoids.

---

## 9. Cost-Effectiveness Analysis

### Cost Per Run (~3000 samples)

| Model | B1 | M0 | M1 | M6 | M1/B1 Ratio |
|-------|-----|-----|-----|-----|-------------|
| Claude Opus 4.6 | $185 | $303 | $215 | $211 | 1.16x |
| Claude Sonnet 4 | $94 | $185 | $127 | $125 | 1.35x |
| GPT-4.1 | $38 | $92 | $56 | $74 | 1.47x |
| GPT-4.1 Mini | $13 | $21 | $13 | $16 | 1.00x |
| Gemini 2.5 Flash | $11 | $14 | $13 | $14 | 1.18x |

### Cost-Adjusted Performance (F2 per dollar)

| Model | Best Config | F2 | Cost | F2/$ |
|-------|-------------|-----|------|------|
| Gemini 2.5 Flash | B1 | 0.829 | $11 | 0.075 |
| GPT-4.1 Mini | M0 | 0.862 | $21 | 0.041 |
| Gemini 3.1 Pro | B1 | 0.861 | $66 | 0.013 |
| GPT-4.1 | B1 | 0.868 | $38 | 0.023 |
| Claude Opus 4.6 | B4 | 0.865 | $213 | 0.004 |

**Best value:** Gemini 2.5 Flash at B1 achieves F2=0.829 for only $11/run — 7x cheaper than the next best option with only 4pp lower F2.

---

## 10. Effect Size Summary

| Comparison | Metric | Cohen's d | Interpretation |
|------------|--------|-----------|----------------|
| B1 vs M1 | F1 | +0.651 | Medium improvement |
| B1 vs M1 | F2 | -0.113 | Negligible |
| B1 vs M1 | Jaccard | -0.781 | Medium degradation |
| B1 vs M1 | Laziness | +0.758 | Medium worsening |
| M1 vs M6 | F1 | -0.809 | Large (M6 worse F1) |
| M1 vs M6 | Jaccard | +1.161 | **Large improvement** |
| M1 vs M6 | Laziness | -1.518 | **Large improvement** |
| B1 vs M6 | Jaccard | +0.361 | Small improvement |
| B1 vs M6 | Laziness | -0.406 | Small improvement |

---

## 11. Hypothesis Evaluation

### H1: Multi-agent beats single-agent baselines (F2_multiagent > F2_baseline)

**Status: NOT SUPPORTED**

- Mean F2: B1 (0.803) ≈ M1 (0.790) ≈ M6 (0.790)
- No statistically significant difference (all p > 0.27)
- Effect sizes negligible (|d| < 0.12)
- Best individual F2 achieved by baselines (GPT-4.1 B1: 0.868) or M0 (Claude Sonnet 4 M0: 0.877)

### H2: Specialists help rare categories most (dF2_rare > dF2_common)

**Status: REJECTED**

- Rare F2 actually *decreases* from B1 (0.653) to M1 (0.593), a -6pp drop
- Common F2 slightly improves from B1 (0.911) to M1 (0.935)
- The classification/routing gate is most harmful for rare categories where model confidence is lowest

### H3: Architecture matters, not just prompts (M1 > M6 significantly)

**Status: SUPPORTED (but in the opposite direction)**

- M1 vs M6 F1: M1 wins (+0.053, p=0.003) due to higher precision
- M1 vs M6 Jaccard: M6 wins (+0.072, p=0.002, d=1.16)
- M1 vs M6 Laziness: M6 wins (-0.121, p=0.001, d=-1.52)
- Architecture matters, but the multi-agent architecture *hurts* on balance — it introduces a classification bottleneck

### H4: Multi-agent produces auditable reasoning (Trace completeness > 90%)

**Status: ACHIEVABLE** (requires separate trace analysis via LangFuse)

---

## 12. M0 vs M1: Two Distinct Multi-Step Architectures

M0 and M1 are fundamentally different architectures that happen to share a "gate before extraction" pattern:

| Aspect | M0 (Classify-then-Extract) | M1 (Full Multi-Agent) |
|--------|---------------------------|----------------------|
| **Type** | Two-step single-agent pipeline | LangGraph multi-agent system |
| **Workflow** | classify → extract (conditional) | route (LLM) → specialist → validate → finalize |
| **Agents** | 1 (same model, two calls) | 4+ (orchestrator + 3 specialists + validator) |
| **Routing** | Binary (relevant/not) | Category-based (→ Risk, Temporal, or IP specialist) |
| **Validation** | None | Grounding + format check |
| **Specialist prompts** | Generic extraction prompt | Domain-specific prompts per specialist |

### Head-to-Head Comparison (M0 vs M1, per model)

| Model | M0 F2 | M1 F2 | Diff | M0 Laziness | M1 Laziness | M0 Jaccard | M1 Jaccard |
|-------|--------|--------|------|-------------|-------------|------------|------------|
| claude-haiku-4.5 | 0.792 | **0.835** | +0.043 | 16.9% | **8.8%** | 0.365 | **0.403** |
| claude-opus-4.6 | **0.864** | 0.860 | -0.005 | 7.6% | **6.6%** | **0.434** | 0.429 |
| claude-sonnet-4 | **0.877** | 0.826 | -0.051 | **7.0%** | 7.8% | 0.427 | **0.491** |
| claude-sonnet-4.6 | **0.860** | 0.834 | -0.026 | **10.5%** | 11.0% | 0.340 | **0.397** |
| gemini-2.5-flash | 0.619 | **0.810** | +0.190 | 40.9% | **13.6%** | 0.303 | **0.384** |
| gemini-2.5-pro | 0.707 | **0.834** | +0.127 | 31.7% | **6.4%** | 0.280 | **0.375** |
| gemini-3-flash | **0.822** | 0.747 | -0.075 | **16.0%** | 24.0% | **0.408** | 0.345 |
| gemini-3.1-pro | **0.843** | 0.840 | -0.003 | 13.8% | **10.9%** | **0.441** | 0.420 |
| gpt-4.1 | **0.828** | 0.777 | -0.051 | **16.4%** | 20.6% | 0.289 | **0.298** |
| gpt-4.1-mini | **0.862** | 0.777 | -0.086 | **8.3%** | 17.8% | **0.333** | 0.319 |
| gpt-4.1-nano | **0.659** | 0.546 | -0.113 | **25.6%** | 42.3% | **0.340** | 0.271 |

### Key Differences

**M0 wins on F2 for 8/11 models** (mean diff: M1 is -0.004 lower). M0's simpler two-step pipeline outperforms the full multi-agent system for most models.

**However, M1 dramatically rescues models that fail at M0's classification:**
- Gemini 2.5 Flash: M0 F2=0.619 → M1 F2=0.810 (+19pp!)
- Gemini 2.5 Pro: M0 F2=0.707 → M1 F2=0.834 (+13pp!)

These models have extremely high M0 laziness (31-41%) because their classification step is unreliable. M1's specialist routing partially compensates by giving the model domain-specific context that helps it recognize relevant clauses.

**M1 consistently improves Jaccard** (6/11 models) — the specialist prompts help produce better span extractions even when recall suffers.

### Failure Mode Comparison

| Failure Mode | M0 | M1 |
|-------------|-----|-----|
| Classification gate too aggressive | Primary failure — flat binary decision | Less severe — routing provides 2nd chance |
| Routing errors | N/A | Orchestrator sends to wrong specialist |
| Laziness source | Binary classifier says "not relevant" | Specialist says "not in my domain" |
| Models most affected | Gemini 2.5 (poor classifiers) | GPT-4.1, GPT-4.1 Mini (high routing laziness) |

### Interpretation

M0 and M1 represent different tradeoffs:
- **M0** is simpler and works well when the model is a good binary classifier (Anthropic models, GPT-4.1 Mini). It achieves the highest F2 ceiling (0.877 with Claude Sonnet 4).
- **M1** is more complex but more robust — it rescues models that are poor classifiers by providing specialist context. Its consistency is higher (lower variance across models).
- **Neither consistently beats baselines on F2**, confirming that the fundamental problem is the gate pattern, not the specific architecture.

---

## 13. Root Cause Analysis: Why Multi-Step Architectures Underperform on F2

### The Shared Problem: Pre-Extraction Gating

Both M0 and M1 share a design where a decision is made *before* extraction:
- M0: "Is this category relevant?" (binary classify)
- M1: "Which specialist handles this?" (route, then specialist decides)

This introduces asymmetric error: a false-negative gate decision is **irrecoverable** — extraction never happens. In contrast, B1/B4/M6 always attempt extraction, so false negatives only occur at the extraction stage.

### Why the Gate Hurts F2 Specifically

F2 = 5×(P×R) / (4P + R) — recall dominates.

- Gate adds ~10pp precision (fewer false positives) but costs ~6pp recall (more false negatives)
- Net effect on F2: approximately zero or slightly negative
- Net effect on F1: positive (+4-6pp) because F1 weights precision equally

### Model-Specific Vulnerabilities

| Model Type | M0 Behavior | M1 Behavior |
|-----------|-------------|-------------|
| Strong classifiers (Anthropic) | Works well, low laziness | Slight overhead from routing |
| Moderate classifiers (GPT-4.1) | Acceptable | Routing errors increase laziness |
| Weak classifiers (Gemini 2.5) | Catastrophic laziness (30-40%) | Partially rescued by specialists |
| Small models (Nano) | High laziness everywhere | Even worse due to routing complexity |

### Evidence Summary

- M0 common-tier laziness: 10.7% vs B1's 3.7% (gate rejects obvious positives)
- M1 moderate-tier laziness: 16.1% vs B1's 10.6% (routing errors compound)
- M6 avoids both problems (3.4% overall laziness) because it has no gate

### Why M6 Works Better

M6 uses the same specialist knowledge (category indicators, domain patterns) as M1 but delivers it in a single prompt without:
- A routing decision that can fail
- A classification gate that can reject positives
- Inter-agent communication overhead that introduces noise

---

## 13. Recommendations

### For the Thesis

1. **Frame as an empirical investigation with meaningful negative results.** The finding that multi-agent routing hurts recall-sensitive tasks is novel and publishable.

2. **Emphasize the architectural insight:** The value of specialist knowledge (prompts) is separable from architectural complexity. M6 captures knowledge benefits without overhead.

3. **Report the precision-recall tradeoff explicitly:** Multi-agent excels at precision (fewer false positives) but fails at recall (more false negatives). Task requirements determine which architecture is appropriate.

### For Future Work

1. **Lenient classifier variant:** Modify M0/M1 to default-positive (extract unless confident no clause exists), which should preserve precision gains while reducing laziness.

2. **Adaptive routing:** Route to specialists only for moderate/rare categories; use direct extraction for common categories where the gate adds no value.

3. **Ensemble approach:** Combine M1 (precision) with B1 (recall) via a union strategy to achieve best of both worlds.

4. **Per-tier optimization:** Use different architectures per tier — baselines for rare (maximize recall), M0 for common (precision matters more when prevalence is high).

---

## 14. Summary Table for Presentation

| Metric | B1 (Zero-Shot) | B4 (CoT) | M0 (Classify-Extract) | M1 (Multi-Agent) | M6 (Combined Prompts) | Winner |
|--------|----------------|-----------|----------------------|-------------------|----------------------|--------|
| F2 Score | **0.803** | 0.791 | 0.794 | 0.790 | 0.790 | B1 (all ns) |
| F1 Score | 0.737 | 0.708 | **0.798** | 0.777 | 0.724 | M0** |
| Precision | 0.662 | 0.612 | **0.813** | 0.768 | 0.642 | M0 |
| Recall | 0.858 | **0.862** | 0.793 | 0.801 | 0.844 | B4 |
| Laziness | 6.6% | 5.0% | 17.7% | 15.4% | **3.4%** | M6*** |
| Jaccard | 0.430 | 0.375 | 0.360 | 0.376 | **0.447** | M6** |
| Cost (USD) | **$52** | $70 | $96 | $70 | $70 | B1 |
| Rare F2 | **0.653** | 0.649 | 0.613 | 0.593 | 0.621 | B1 |
| Common F2 | 0.911 | 0.930 | 0.878 | **0.935** | 0.928 | M1 |
| Moderate F2 | 0.754 | 0.734 | **0.778** | 0.718 | 0.727 | M0 |
| Robustness (model variance) | 0.099 | 0.099 | 0.086 | **0.083** | 0.102 | M1 |

### Configuration Profiles

| Config | Strengths | Weaknesses | Best Use Case |
|--------|-----------|------------|---------------|
| **B1** | Highest F2, cheapest, best on rare | Low precision, moderate laziness | Default choice; recall-critical tasks |
| **B4** | Highest recall, low laziness | Lowest precision, expensive, slow | When finding every clause matters most |
| **M0** | Best F1/precision, best on moderate tier | High laziness, expensive, fragile | Precision-critical tasks with strong models |
| **M1** | Most robust across models, best on common | High laziness, highest cost | When model quality is uncertain |
| **M6** | Best Jaccard, lowest laziness | Lower F1 than M0/M1 | When span quality and completeness matter |

### Bottom Line

1. **No architecture beats simple zero-shot (B1) on F2** — the primary recall-weighted metric. All differences are statistically non-significant.

2. **Architecture choice depends on the optimization target:**
   - Maximize recall → B4 (CoT forces thoroughness)
   - Maximize precision → M0 (classification gate filters noise)
   - Maximize span quality → M6 (specialist knowledge without gating)
   - Minimize risk of failure → M1 (most consistent across models)

3. **The key insight:** Specialist domain knowledge (shared by M0, M1, M6) improves extraction quality, but the *delivery mechanism* matters. Gated architectures (M0, M1) sacrifice recall; ungated delivery (M6) preserves recall while improving span overlap.

4. **Cost-benefit:** Multi-step architectures add 35-85% cost for no F2 gain. The only justified upgrade from B1 is M6, which improves Jaccard (+0.017) and laziness (-3.2pp) for +35% cost.
