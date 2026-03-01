# Progress Tracker

Last updated: 2026-02-16

## Summary

| Area                 | Status      | Details                                                         | Note |
| -------------------- | ----------- | --------------------------------------------------------------- | ---- |
| Core Infrastructure  | Done        | Data loader, model client, prompt registry, metrics, statistics |      |
| Baselines (B1, B4)   | Done        | Implemented + calibration runs completed                        |      |
| Multi-Agent (M1)     | Done        | Orchestrator + 3 specialists + validation implemented           |      |
| Ablation (M6)        | Done        | Combined prompts baseline implemented                           |      |
| Dashboard            | Done        | Full visualization with interactive tables                      |      |
| Tests                | Done        | 81 tests passing                                                |      |
| Full Experiment Runs | In Progress | Need runs across all 19 models                                  |      |
| Statistical Analysis | In Progress | Framework ready, needs full run data                            |      |
| Thesis Writing       | Not Started |                                                                 |      |

---

## Phase 1: Infrastructure

### Data Loading

- [x] CUAD dataset loader (`src/data/cuad_loader.py`)
- [x] Local JSON + HuggingFace fallback loading
- [x] Category tier stratification (common/moderate/rare)
- [x] Stratified sampling with seed control
- [x] CUADSample dataclass with contract_text, category, question, ground_truth

### Model Client

- [x] Unified `invoke_model()` for all providers (`src/models/client.py`)
- [x] Anthropic provider (Claude Sonnet 4)
- [x] OpenAI provider (GPT 4.1, GPT 4.1 Mini)
- [x] Google provider (Gemini 2.5 Pro)
- [x] Ollama provider (15 open-source models)
- [x] Model config registry with 19 models (`src/models/config.py`)
- [x] LangFuse integration for observability
- [x] Token/cost/latency diagnostics (`src/models/diagnostics.py`)

### Prompt System

- [x] YAML-based PromptRegistry (`src/prompts/registry.py`)
- [x] PromptTemplate with version, description, system prompt
- [x] Baseline prompts: zero_shot, chain_of_thought, combined_prompts
- [x] Specialist prompts: risk_liability, temporal_renewal, ip_commercial
- [x] Common extraction base with anti-laziness instructions

### Evaluation Metrics

- [x] F1, F2 score computation (`src/evaluation/metrics.py`)
- [x] Jaccard similarity (span overlap)
- [x] Laziness rate (false "no clause" responses)
- [x] Grounding rate (extracted text in source)
- [x] Single-sample evaluation (`evaluate_single`)
- [x] Batch evaluation (`evaluate_batch`)
- [x] TP/FP/FN/TN classification matching ContractEval definitions

### Statistical Analysis

- [x] Bootstrap confidence intervals (`src/evaluation/statistical.py`)
- [x] McNemar test (paired binary outcomes)
- [x] Wilcoxon signed-rank test (paired continuous)
- [x] Benjamini-Hochberg correction (multiple comparisons)
- [x] Cohen's d effect size
- [x] Result formatting utility

### Tests

- [x] Metrics tests -- 30+ test cases (`tests/test_metrics.py`)
- [x] Data loader tests (`tests/test_data_loader.py`)
- [x] Agent tests (`tests/test_agents.py`)
- [x] Statistical tests (`tests/test_statistical.py`)
- [x] All 81 tests passing

---

## Phase 2: Baselines

### B1 -- Zero-Shot (ContractEval Replication)

- [x] Implementation (`src/baselines/zero_shot.py`)
- [x] Exact ContractEval prompt match
- [x] Prompt stored in `prompts/baselines/zero_shot.yaml`
- [x] Calibration run with Claude Sonnet 4 (45 samples, 10/tier)
- [x] Results: F2=0.839, F1=0.847, Precision=0.862, Recall=0.833
- [x] Laziness rate: 10% (above 3% target -- needs investigation)
- [x] Per-tier: Common=0.900, Moderate=0.962, Rare=0.638
- [x] Cost: $1.22 for 45 samples, Duration: 183s

### B4 -- Chain-of-Thought

- [x] Implementation (`src/baselines/chain_of_thought.py`)
- [x] Step-by-step reasoning prompt
- [x] Prompt stored in `prompts/baselines/chain_of_thought.yaml`
- [ ] Calibration run (not yet executed)

### Notebook 03 -- Baseline Calibration

- [x] Stratified sampling (common/moderate/rare tiers)
- [x] Extraction loop with crash-safe JSONL resume
- [x] Metrics computation (F1, F2, Jaccard, laziness, per-tier)
- [x] Diagnostics capture (tokens, cost, latency)
- [x] Summary JSON + intermediate JSONL output
- [x] Supports B1 and B4 configurations
- [x] M-variants removed (moved to notebook 04)

---

## Phase 3: Multi-Agent System

### Agent Framework

- [x] BaseAgent abstract class (`src/agents/base.py`)
- [x] AgentConfig dataclass (name, model_key, prompt_name, categories)
- [x] ExtractionResult model (extracted_clauses, reasoning, confidence)
- [x] LangGraph state definitions (`src/agents/state.py`)
- [x] Memory/SQLite checkpointing (`src/agents/checkpointing.py`)

### M1 -- Full Multi-Agent System

- [x] Orchestrator with LangGraph routing (`src/agents/orchestrator.py`)
- [x] CATEGORY_ROUTING map (41 categories -> 3 specialists)
- [x] Risk & Liability specialist -- 13 categories (`src/agents/risk_liability.py`)
- [x] Temporal/Renewal specialist -- 11 categories (`src/agents/temporal_renewal.py`)
- [x] IP & Commercial specialist -- 17 categories (`src/agents/ip_commercial.py`)
- [x] Validation agent -- grounding + format check (`src/agents/validation.py`)
- [x] Specialist prompts with domain indicators (`prompts/specialists/*.yaml`)
- [x] Wired into `scripts/run_experiment.py`
- [x] Test run completed (Claude Sonnet 4, 45 samples)

### M6 -- Combined Prompts Ablation

- [x] Implementation (`src/baselines/combined_prompts.py`)
- [x] All specialist prompts combined into single agent
- [x] Prompt stored in `prompts/baselines/combined_prompts.yaml`
- [ ] Full calibration run (not yet executed)

### M2-M5 -- Additional Ablations

- [ ] M2: Orchestrator + specialists, no validation
- [ ] M3: Orchestrator + 1 generalist specialist
- [ ] M4: Orchestrator + specialists with different routing
- [ ] M5: Direct specialist calls, no orchestrator

- Note: These are optional stretch goals; minimum scope is B1, B4, M1, M6

### Notebook 04 -- Multi-Agent Experiment

- [x] Config cell with EXPERIMENT_TYPE selector (M1-M6)
- [x] Same stratified sampling as notebook 03 (fair comparison)
- [x] M1 extraction with orchestrator + trace capture
- [x] M6 extraction with combined prompts
- [x] M2-M5 placeholders (NotImplementedError)
- [x] Metrics computation (matches notebook 03)
- [x] Statistical comparison framework (H1-H4)
- [x] Loads baseline results from experiments/results/
- [x] Summary comparison table
- [x] Architecture info saved in summary JSON

---

## Phase 4: Experiment Runs

### Claude Sonnet 4 (Primary Model)

- [x] B1 zero-shot calibration (10/tier = 45 samples)
- [x] M1 multi-agent test run (45 samples)
- [ ] B4 chain-of-thought run
- [ ] M6 combined prompts run
- [ ] Full-scale runs (larger sample sizes for statistical power)

### Cross-Model Evaluation

- [ ] GPT 4.1
- [ ] GPT 4.1 Mini
- [ ] Gemini 2.5 Pro
- [ ] DeepSeek R1 variants (2 models)
- [ ] LLaMA 3.1 8B
- [ ] Gemma 3 4B, 3 12B
- [ ] Qwen3 4B, 8B, 14B (thinking + non-thinking)
- [ ] Qwen3 8B AWQ, 8B FP8

---

## Phase 5: Dashboard

### Core Pages

- [x] Experiments list page with interactive table
- [x] Experiment detail page with tabbed views
- [x] Sample detail page with contract viewer
- [x] API routes for experiments, samples

### Features

- [x] Search experiments by model/provider/run_id
- [x] Filter by config type (B1/B4/M1/M6)
- [x] Sort by any column (F1, F2, Jaccard, etc.)
- [x] Clickable rows for drill-down navigation
- [x] Metrics grid (F1, F2, Precision, Recall, Jaccard, Laziness)
- [x] Confusion matrix visualization
- [x] Classification pie chart (TP/FP/FN/TN)
- [x] Per-tier breakdown (common/moderate/rare)
- [x] Samples table with tier/classification filtering
- [x] Agent routing column for M1 runs
- [x] Contract text viewer with clause highlighting
- [x] Usage details (tokens, latency)
- [x] Agent trace visualization (M1 node traversal)
- [x] Diagnostics cards (token usage, cost, latency)
- [x] Config tab -- system prompt (baselines), architecture view (M1)
- [x] Architecture view: workflow, specialist details, routing table
- [x] Handles both baseline and multi-agent result formats

### Tech Stack

- [x] Next.js 16 with App Router
- [x] React 19, TypeScript
- [x] shadcn/ui component library
- [x] Recharts for visualizations
- [x] Tailwind CSS 4
- [x] Server components for data loading
- [x] Client components for interactivity (search, sort, filter)

---

## Phase 6: Statistical Analysis & Results

### Hypothesis Testing (framework ready, needs full data)

- [x] Statistical functions implemented
- [ ] H1: M1 F2 > B1 F2 (McNemar + Cohen's d)
- [ ] H2: Per-tier F2 comparison (dF2_rare > dF2_common)
- [ ] H3: M1 > M6 (McNemar)
- [ ] H4: Trace completeness > 90%
- [ ] Bootstrap CIs for all primary metrics
- [ ] Benjamini-Hochberg correction across tests

### Cross-Model Analysis

- [ ] Side-by-side comparison table across all 19 models
- [ ] Per-tier performance heat map
- [ ] Cost-accuracy tradeoff analysis
- [ ] Open-source vs proprietary comparison

---

## Phase 7: Documentation & Thesis

### Code Documentation

- [x] CLAUDE.md -- project specification
- [x] README.md -- project overview and quickstart
- [x] PROGRESS.md -- this file
- [x] .env.example -- environment template
- [x] Docstrings on all public functions
- [x] Type hints throughout

### Thesis Writing

- [ ] Chapter 1: Introduction
- [ ] Chapter 2: Related Work
- [ ] Chapter 3: Methodology
- [ ] Chapter 4: Implementation
- [ ] Chapter 5: Evaluation
- [ ] Chapter 6: Discussion
- [ ] Chapter 7: Conclusion

---

## Known Issues

1. **Laziness rate**: B1 zero-shot shows 10% laziness rate vs 3% target. Needs investigation -- may be model-specific or prompt-related.
2. **M2-M5 ablations**: Not implemented. These are stretch goals and may be cut if timeline is tight.
3. **B4 calibration**: Chain-of-thought baseline not yet run. Needed for completeness before statistical comparison.
4. **Full-scale runs**: Current runs use 10 samples/tier (45 total). Need larger samples for statistical power in hypothesis testing.
5. **Cross-model runs**: Only Claude Sonnet 4 has been tested so far. Need to run all 19 models for the full ContractEval comparison.

---

## What To Do Next

1. **Run B4 baseline** (notebook 03) -- execute B4 chain-of-thought with Claude Sonnet 4
2. **Run M6 ablation** (notebook 04) -- execute M6 combined prompts with Claude Sonnet 4
3. **Compare M1 vs B1 vs M6** -- run statistical tests (H1, H3) once all configs have results
4. **Increase sample size** -- run B1 and M1 with more samples/tier for statistical power
5. **Cross-model evaluation** -- run B1 across all 19 models to replicate ContractEval
6. **Investigate laziness** -- analyze why B1 laziness rate is 10% instead of target 3%
7. **Begin thesis writing** -- start Chapter 3 (Methodology) and Chapter 4 (Implementation)
