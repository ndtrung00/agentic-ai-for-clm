# Experiment Design: Model Selection & Sample Size Rationale

**Author:** Trung Nguyen
**Date:** 2 March 2026
**Purpose:** Document the reasoning behind model selection, sample sizes, and experiment matrix. Serves as reference for thesis Chapter 4 (Methodology).

---

## 1. Dataset Overview

**Source:** CUAD (Contract Understanding Atticus Dataset), test split

| Metric                  | Value                          |
| ----------------------- | ------------------------------ |
| Total samples           | 20,910                         |
| Unique contracts        | 510                            |
| Categories              | 41 clause types                |
| Average contract length | ~52,500 chars (median ~33,000) |
| Max contract length     | ~338,000 chars                 |

### Tier Stratification (by ContractEval F1 performance)

| Tier                   | Samples    | Categories | Positive  | Negative   |
| ---------------------- | ---------- | ---------- | --------- | ---------- |
| Common (F1 > 0.7)      | 2,574      | 6          | 2,278     | 296        |
| Moderate (F1 0.3--0.7) | 7,722      | 14         | 2,050     | 5,672      |
| Rare (F1 near zero)    | 7,293      | 21         | 812       | 6,481      |
| **Total**              | **20,910** | **41**     | **5,140** | **12,449** |

---

## 2. Sample Size Determination

### 2.1 Statistical Requirements

Three constraints drive the minimum sample size:

**McNemar's test** (primary significance test for paired binary comparisons):

- Requires ~30 discordant pairs for 80% power at alpha=0.05
- Requires ~50 discordant pairs for 90% power
- With a typical 20% disagreement rate between models, this means 150--250 samples minimum for overall comparison

**Bootstrap confidence intervals** (95% CI for F2, Jaccard):

- 385 samples gives CI width of +/-0.05
- 1,068 samples gives CI width of +/-0.03
- 2,401 samples gives CI width of +/-0.02

**Per-tier significance** (needed for H2: "specialists help rare categories most"):

- Each tier needs enough samples independently for McNemar within that tier
- The rare tier is the bottleneck: 21 categories means samples spread thin

### 2.2 Chosen Configuration: 900 Samples Per Run

```
samples_per_tier = 200
```

Per tier:

- 200 positive samples (from SAMPLES_PER_TIER)
- 100 negative samples (SAMPLES_PER_TIER // 2)
- = 300 per tier

**3 tiers x 300 = 900 samples per run**

### 2.3 Why 900 Samples Is Sufficient

| Analysis Level            | Requirement                  | At n=900                                                                 |
| ------------------------- | ---------------------------- | ------------------------------------------------------------------------ |
| Overall McNemar           | 30--50 discordant pairs      | ~180 discordant pairs (at 20% rate) -- well above threshold              |
| Overall bootstrap CI      | Width < +/-0.05              | CI width ~+/-0.033 -- sufficient for detecting 3--5% differences         |
| Per-tier McNemar          | 30 discordant pairs per tier | ~60 per tier (at 20% rate) -- sufficient                                 |
| Per-category descriptive  | >=5 samples per category     | ~22 samples/category average -- sufficient for descriptive F2            |
| Per-category significance | >=20 samples per category    | Marginal for some rare categories (21 cats share 300 samples = ~14 each) |

### 2.4 Why Not More or Fewer?

**Why not 300 (samples_per_tier=100)?**

- Only ~7 samples per category -- too thin for per-category analysis
- Per-tier bootstrap CIs too wide (+/-0.06) for the ~3--5% differences we expect between configs

**Why not 1,800 (samples_per_tier=400)?**

- Doubles cost for diminishing returns at the overall and per-tier level
- Would strengthen per-category analysis but per-category F2 is descriptive in the thesis, not hypothesis-tested

**Why not the full 20,910?**

- Cost prohibitive: ~$200+ per proprietary model per run, x12 runs = $2,400+
- Diminishing statistical returns: CIs already tight at n=900
- Time: each full run would take hours instead of minutes

### 2.5 Negative Sample Inclusion

Negative samples (ground truth is empty) are included at a 2:1 positive-to-negative ratio because:

- **Required for FP/TN computation:** without negatives, we cannot measure precision or laziness rate
- **Laziness detection:** the laziness problem (models responding "No related clause" when clauses exist) is a key research concern; negative samples calibrate the false positive rate
- **Real distribution is 30/70 pos/neg:** we already oversample positives (67% vs real 30%) to maximize rare category coverage, while still including enough negatives for valid precision metrics

### 2.6 Contract Length Cutoff

```
MAX_CONTRACT_CHARS = 100,000
```

- Cuts off the top ~16% longest contracts (those above 100k chars)
- Necessary to avoid token limit issues, especially with smaller models and models with 128k context windows
- ContractEval used similar truncation strategies
- 84% of contracts (430 of 510) fall within this limit

---

## 3. Model Selection

### 3.1 Available Models

19 models across proprietary and open-source:

**Proprietary (4):** gpt-4.1, gpt-4.1-mini, claude-sonnet-4, gemini-2.5-pro
**Open-source via Ollama (15):** Various Qwen3, DeepSeek, LLaMA, Gemma variants (4B--14B)

### 3.2 Selection Principles

1. **Cross-provider coverage:** results must not be provider-specific; reviewers should not be able to say "only tested on GPT"
2. **Size variation:** test whether model size affects baseline vs. multi-agent delta
3. **Cost efficiency:** B1 is not the main contribution -- invest enough to establish robust baselines, not more
4. **Paired comparison validity:** M1/M6 experiments must use models that also have B1/B4 baselines for direct paired testing

---

## 4. Experiment Matrix

### 4.1 B1: Zero-Shot Baseline (5 models)

B1 replicates the ContractEval methodology (exact prompt match). Its purpose is to:

- **Calibrate** against published ContractEval numbers (GPT-4 F1=0.641, F2=0.678)
- **Establish the performance floor** that multi-agent must beat
- **Show cross-provider generalization** of the zero-shot approach

| Model           | Provider  | Why included                                                           |
| --------------- | --------- | ---------------------------------------------------------------------- |
| gpt-4.1         | OpenAI    | Closest to ContractEval's GPT-4; primary calibration target            |
| gpt-4.1-mini    | OpenAI    | Cost-effective proprietary; shows size/cost scaling within same family |
| claude-sonnet-4 | Anthropic | Different provider; proves baseline isn't GPT-specific                 |
| gemini-2.5-pro  | Google    | Third provider for robustness; different architecture/training         |
| qwen3-8b        | Ollama    | Open-source representative; establishes proprietary/open-source gap    |

**Why 5 models:** B1 needs breadth because it defines the baseline landscape. Every subsequent comparison (B4, M1, M6) references these B1 numbers. Insufficient B1 coverage would weaken all downstream claims.

### 4.2 B4: Chain-of-Thought Baseline (2--3 models)

B4 adds CoT prompting to the zero-shot approach. Its purpose is narrower:

- **Measure the prompting-only uplift** (B1 -> B4 delta)
- **Isolate the "better prompting" effect** from architectural changes
- **Support H3:** if M1 > B4, the improvement comes from architecture, not just richer prompting

| Model        | Provider | Why included                                                 |
| ------------ | -------- | ------------------------------------------------------------ |
| gpt-4.1-mini | OpenAI   | Primary workhorse; shows CoT uplift on a mid-tier model      |
| gpt-4.1      | OpenAI   | Tests diminishing returns: does CoT help strong models less? |
| qwen3-8b     | Ollama   | Tests if CoT helps weak models more (expected: yes)          |

**Why fewer than B1:** B4's research question is about the **delta** from B1, not absolute performance. Since we already have B1 numbers for these models, each B4 run is a direct paired comparison. Running B4 on claude-sonnet-4 and gemini-2.5-pro would tell the same story (CoT helps by X%) at double the cost with marginal thesis value.

**Why these 3 specifically:**

- gpt-4.1 vs gpt-4.1-mini: tests whether CoT benefit scales with model capability (hypothesis: smaller models benefit more)
- qwen3-8b: tests whether CoT can partially close the proprietary/open-source gap (hypothesis: yes, but not fully)

### 4.3 M1: Full Multi-Agent System (2 models)

M1 is the main contribution: orchestrator + 3 specialists + validation layer. Its purpose:

- **Test H1:** multi-agent beats single-agent baselines
- **Test H2:** specialists help rare categories most
- **Test H4:** multi-agent produces auditable reasoning traces

| Model        | Provider | Why included                                                     |
| ------------ | -------- | ---------------------------------------------------------------- |
| gpt-4.1-mini | OpenAI   | Mid-tier proprietary; where multi-agent is most likely to help   |
| qwen3-8b     | Ollama   | Weak model; tests if architecture compensates for model weakness |

**Why only 2 models:** M1 runs are expensive (multiple LLM calls per sample: orchestrator + specialist + validator). Cost per run is 3--5x a baseline run. Two carefully chosen models are sufficient because:

- gpt-4.1-mini is the practical deployment target (good cost/performance ratio)
- qwen3-8b tests the hypothesis that weaker models benefit more from multi-agent decomposition
- Both have B1 and B4 baselines, enabling the full B1 -> B4 -> M1 comparison chain

### 4.4 M6: Combined Prompts Ablation (2 models)

M6 uses the same specialist knowledge as M1 but in a single-agent prompt (no routing, no separate specialists). Its purpose:

- **Test H3:** architecture matters, not just prompts
- **Isolate the multi-agent overhead:** if M1 ~ M6, the architecture adds cost without benefit; if M1 > M6, the decomposition itself provides value

| Model        | Provider | Why included                                                          |
| ------------ | -------- | --------------------------------------------------------------------- |
| gpt-4.1-mini | OpenAI   | Direct comparison: same model, same knowledge, different architecture |
| qwen3-8b     | Ollama   | Same comparison on a weaker model                                     |

**Why same models as M1:** M6 must use identical models to M1 for the ablation to be valid. The comparison is M1 vs M6 on the same model with the same samples -- any difference is attributable to architecture alone.

### 4.5 Full Experiment Matrix

| Model           | B1    | B4    | M1    | M6    | Total runs |
| --------------- | ----- | ----- | ----- | ----- | ---------- |
| gpt-4.1         | x     | x     |       |       | 2          |
| gpt-4.1-mini    | x     | x     | x     | x     | 4          |
| claude-sonnet-4 | x     |       |       |       | 1          |
| gemini-2.5-pro  | x     |       |       |       | 1          |
| qwen3-8b        | x     | x     | x     | x     | 4          |
| **Total**       | **5** | **3** | **2** | **2** | **12**     |

### 4.6 Cost Estimate

| Config              | Runs   | Samples/run | Cost/sample (approx) | Subtotal       |
| ------------------- | ------ | ----------- | -------------------- | -------------- |
| B1 (proprietary x3) | 3      | 900         | $0.01--0.05          | $30--135       |
| B1 (open-source x1) | 1      | 900         | ~$0                  | $0             |
| B1 (gpt-4.1)        | 1      | 900         | ~$0.05               | ~$45           |
| B4 (proprietary x2) | 2      | 900         | $0.01--0.05          | $20--90        |
| B4 (open-source x1) | 1      | 900         | ~$0                  | $0             |
| M1 (proprietary x1) | 1      | 900         | $0.03--0.15          | $27--135       |
| M1 (open-source x1) | 1      | 900         | ~$0                  | $0             |
| M6 (proprietary x1) | 1      | 900         | $0.01--0.05          | $9--45         |
| M6 (open-source x1) | 1      | 900         | ~$0                  | $0             |
| **Total**           | **12** | **10,800**  |                      | **~$130--450** |

Note: M1 cost per sample is higher because each sample involves 2--4 LLM calls (orchestrator routing + specialist extraction + validation).

---

## 5. Hypothesis-to-Experiment Mapping

| Hypothesis                         | Required comparisons                    | Data needed                                    |
| ---------------------------------- | --------------------------------------- | ---------------------------------------------- |
| **H1:** Multi-agent > single-agent | M1 vs B1, M1 vs B4 (same model, paired) | B1 + B4 + M1 on gpt-4.1-mini and qwen3-8b      |
| **H2:** Specialists help rare most | M1 per-tier F2 delta vs B1              | Per-tier breakdown of M1 and B1 on same models |
| **H3:** Architecture > prompts     | M1 vs M6 (same model, same knowledge)   | M1 + M6 on gpt-4.1-mini and qwen3-8b           |
| **H4:** Auditable reasoning        | M1 trace completeness                   | M1 runs with LangFuse tracing enabled          |

Every hypothesis is testable with the 12-run matrix. No hypothesis requires additional runs.

---

## 6. Statistical Tests Applied Per Comparison

| Comparison              | Test                       | Why                                               |
| ----------------------- | -------------------------- | ------------------------------------------------- |
| M1 vs B1 overall        | McNemar (paired binary)    | Same samples, binary correct/incorrect            |
| M1 vs B1 per-tier       | McNemar per tier           | Separate tests, Benjamini-Hochberg correction     |
| M1 vs B4 overall        | McNemar                    | Same as above                                     |
| M1 vs M6 overall        | McNemar                    | Architecture ablation                             |
| F2 confidence intervals | Bootstrap (1000 resamples) | Non-parametric, no distribution assumptions       |
| Effect size             | Cohen's d                  | Standardized effect magnitude                     |
| Multiple comparisons    | Benjamini-Hochberg         | Controls false discovery rate across 4 hypotheses |

Following Dror et al. (ACL 2018) methodology throughout.
