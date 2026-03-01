# Experiment Checklist

Last updated: 2026-03-01

---

## Calibration Targets (ContractEval Paper, GPT-4.1)


| Metric             | ContractEval Reference | Thesis Success Criteria |
| ------------------ | ---------------------- | ----------------------- |
| F1                 | 0.641                  | —                       |
| F2                 | 0.678                  | > 0.73 (multi-agent)    |
| F2 (rare)          | ~0.15                  | > 0.40 (multi-agent)    |
| Jaccard            | 0.472                  | > 0.50                  |
| Laziness rate      | 7.1%                   | < 3%                    |
| Trace completeness | —                      | > 90%                   |
| Grounding rate     | —                      | > 95%                   |


---

## 1. Calibration Runs (10/tier = 45 samples)

Small-scale runs to verify implementation correctness before committing to full dataset.

### B1 — Zero-Shot


| Model              | Status      | F1    | F2    | Laziness | Notes                        |
| ------------------ | ----------- | ----- | ----- | -------- | ---------------------------- |
| Claude Sonnet 4    | Done        | 0.847 | 0.839 | 10%      | 2x duplicate runs exist      |
| Claude Sonnet 4.6  | Not started |       |       |          |                              |
| Claude Opus 4.6    | Not started |       |       |          |                              |
| Claude Haiku 4.5   | Not started |       |       |          |                              |
| GPT-4.1            | Not started |       |       |          | ContractEval reference model |
| GPT-4.1 Mini       | Not started |       |       |          |                              |
| Gemini 2.5 Pro     | Not started |       |       |          |                              |
| Gemini 2.5 Flash   | Not started |       |       |          |                              |
| Gemini 3 Flash     | Not started |       |       |          | Preview                      |
| Gemini 3.1 Pro     | Not started |       |       |          | Preview                      |


### B4 — Chain-of-Thought


| Model              | Status      | F1    | F2    | Laziness | Notes                                     |
| ------------------ | ----------- | ----- | ----- | -------- | ----------------------------------------- |
| Claude Sonnet 4    | Not started |       |       |          |                                           |
| Claude Sonnet 4.6  | Not started |       |       |          |                                           |
| Claude Opus 4.6    | Not started |       |       |          |                                           |
| Claude Haiku 4.5   | Not started |       |       |          |                                           |
| GPT-4.1            | Not started |       |       |          |                                           |
| GPT-4.1 Mini       | Done        | 0.732 | 0.807 | 0%       | Over-extraction issue under investigation |
| Gemini 2.5 Pro     | Not started |       |       |          |                                           |
| Gemini 2.5 Flash   | Not started |       |       |          |                                           |
| Gemini 3 Flash     | Not started |       |       |          | Preview                                   |
| Gemini 3.1 Pro     | Not started |       |       |          | Preview                                   |


### M1 — Multi-Agent (Full System)


| Model              | Status      | F1    | F2    | Laziness | Notes                    |
| ------------------ | ----------- | ----- | ----- | -------- | ------------------------ |
| Claude Sonnet 4    | Done        | 0.714 | 0.685 | 13.3%    | Only 5/tier (21 samples) |
| Claude Sonnet 4.6  | Not started |       |       |          |                          |
| Claude Opus 4.6    | Not started |       |       |          |                          |
| Claude Haiku 4.5   | Not started |       |       |          |                          |
| GPT-4.1            | Not started |       |       |          |                          |
| GPT-4.1 Mini       | Not started |       |       |          |                          |
| Gemini 2.5 Pro     | Not started |       |       |          |                          |
| Gemini 2.5 Flash   | Not started |       |       |          |                          |
| Gemini 3 Flash     | Not started |       |       |          | Preview                  |
| Gemini 3.1 Pro     | Not started |       |       |          | Preview                  |


### M6 — Combined Prompts Ablation


| Model              | Status      | F1  | F2  | Laziness | Notes   |
| ------------------ | ----------- | --- | --- | -------- | ------- |
| Claude Sonnet 4    | Not started |     |     |          |         |
| Claude Sonnet 4.6  | Not started |     |     |          |         |
| Claude Opus 4.6    | Not started |     |     |          |         |
| Claude Haiku 4.5   | Not started |     |     |          |         |
| GPT-4.1            | Not started |     |     |          |         |
| GPT-4.1 Mini       | Not started |     |     |          |         |
| Gemini 2.5 Pro     | Not started |     |     |          |         |
| Gemini 2.5 Flash   | Not started |     |     |          |         |
| Gemini 3 Flash     | Not started |     |     |          | Preview |
| Gemini 3.1 Pro     | Not started |     |     |          | Preview |


---

## 2. Full Dataset Runs (all 102 contracts / 4,128 data points)

Full-scale runs for statistical significance. Only proceed after calibration looks reasonable.

### B1 — Zero-Shot (Full)

- Claude Sonnet 4
- Claude Sonnet 4.6
- Claude Opus 4.6
- Claude Haiku 4.5
- GPT-4.1 (primary — ContractEval replication)
- GPT-4.1 Mini
- Gemini 2.5 Pro
- Gemini 2.5 Flash
- Gemini 3 Flash (Preview)
- Gemini 3.1 Pro (Preview)

### B4 — Chain-of-Thought (Full)

- Claude Sonnet 4
- Claude Sonnet 4.6
- Claude Opus 4.6
- Claude Haiku 4.5
- GPT-4.1
- GPT-4.1 Mini
- Gemini 2.5 Pro
- Gemini 2.5 Flash
- Gemini 3 Flash (Preview)
- Gemini 3.1 Pro (Preview)

### M1 — Multi-Agent (Full)

- Claude Sonnet 4
- Claude Sonnet 4.6
- Claude Opus 4.6
- Claude Haiku 4.5
- GPT-4.1
- GPT-4.1 Mini
- Gemini 2.5 Pro
- Gemini 2.5 Flash
- Gemini 3 Flash (Preview)
- Gemini 3.1 Pro (Preview)

### M6 — Combined Prompts (Full)

- Claude Sonnet 4
- Claude Sonnet 4.6
- Claude Opus 4.6
- Claude Haiku 4.5
- GPT-4.1
- GPT-4.1 Mini
- Gemini 2.5 Pro
- Gemini 2.5 Flash
- Gemini 3 Flash (Preview)
- Gemini 3.1 Pro (Preview)

---

## 3. Open-Source Model Evaluation (B1 only, for cross-model comparison)

These run B1 zero-shot to compare across model families. Full dataset preferred; calibration acceptable if resource-constrained.

### DeepSeek

- DeepSeek R1 Distill Qwen 7B
- DeepSeek R1 0528 Qwen3 8B

### LLaMA

- LLaMA 3.1 8B Instruct

### Gemma

- Gemma 3 4B
- Gemma 3 12B

### Qwen3 (non-thinking)

- Qwen3 4B
- Qwen3 8B
- Qwen3 14B

### Qwen3 (thinking)

- Qwen3 4B Thinking
- Qwen3 8B Thinking
- Qwen3 14B Thinking

### Qwen3 (quantized)

- Qwen3 8B AWQ
- Qwen3 8B AWQ Thinking
- Qwen3 8B FP8
- Qwen3 8B FP8 Thinking

---

## 4. Statistical Analysis

### Hypothesis Testing

- H1: M1 F2 > B1 F2 (McNemar + bootstrap CI + Cohen's d, p < 0.05)
- H2: dF2_rare > dF2_common (per-tier comparison)
- H3: M1 > M6 significantly (architecture vs prompting)
- H4: Trace completeness > 90% (multi-agent explainability)
- Benjamini-Hochberg correction across all tests

### Cross-Model Analysis

- Side-by-side comparison table (all models, all configs)
- Per-tier performance heat map
- Cost-accuracy tradeoff analysis
- Open-source vs proprietary comparison
- Thinking vs non-thinking Qwen3 comparison

---

## 5. Known Issues to Resolve

- **Laziness rate**: B1 Claude Sonnet 4 shows 10%, M1 shows 13.3% — both above 3% target
- **B4 over-extraction**: GPT-4.1 Mini has 0% laziness but may be over-extracting (current branch)
- **M1 calibration**: Only 21 samples (5/tier) — need at least 10/tier calibration before full run
- **Duplicate B1 runs**: Two identical Claude Sonnet 4 B1 results — clean up

---

## 6. Thesis Writing

- Chapter 1: Introduction
- Chapter 2: Related Work
- Chapter 3: Methodology
- Chapter 4: Implementation
- Chapter 5: Evaluation
- Chapter 6: Discussion
- Chapter 7: Conclusion

---

## Priority Order

1. Fix B4 over-extraction issue (current branch)
2. Complete calibration matrix for proprietary models (B1, B4, M1, M6 x 4 models)
3. Run full-dataset B1 on GPT-4.1 (ContractEval replication — this is the anchor)
4. Run full-dataset B1 + B4 on remaining proprietary models
5. Run full-dataset M1 + M6 on proprietary models
6. Statistical analysis (H1–H4)
7. Open-source model sweep (B1 only)
8. Thesis writing

