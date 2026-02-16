# Multi-Agent Contract Analysis System

Master's thesis implementation investigating whether multi-agent architectures can improve contract clause extraction beyond single-agent LLM baselines using the CUAD dataset.

**Author:** Trung Nguyen
**Institution:** TU München, Department of Informatics
**Supervisor:** Prof. Dr. Ingo Weber
**Timeline:** October 2025 -- April 2026

## Research Question

> Can a multi-agent framework improve contract clause extraction accuracy beyond single-agent baselines while providing superior explainability?

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                      │
│       Routes queries to specialists by category     │
│              (LangGraph state machine)              │
└─────────────────────────────────────────────────────┘
              │              │              │
              ▼              ▼              ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ RISK & LIABILITY│ │TEMPORAL/RENEWAL │ │ IP & COMMERCIAL │
│  (13 categories)│ │  (11 categories)│ │  (17 categories)│
└─────────────────┘ └─────────────────┘ └─────────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                  ┌─────────────────────┐
                  │   VALIDATION AGENT  │
                  │  Grounding & Format │
                  └─────────────────────┘
```

The orchestrator routes each contract category to its domain specialist agent. Each specialist uses category-specific indicators and anti-laziness prompting to extract exact clause text. A validation layer checks grounding (extracted text exists in source) and format compliance.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js 18+ (for dashboard)
- API keys for at least one LLM provider (Anthropic, OpenAI, or Google)
- Optional: [Ollama](https://ollama.com) for running open-source models locally

### Setup

```bash
# Clone and install
git clone <repo-url>
cd agentic-ai-for-clm

# Install Python dependencies
uv sync --all-extras

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Verify installation
uv run pytest tests/ -v
```

### Running Experiments

**Via notebooks (recommended for interactive use):**

```bash
# Launch Jupyter
uv run jupyter notebook

# Open notebooks/03_baseline_calibration.ipynb for baselines (B1, B4)
# Open notebooks/04_multiagent_experiment.ipynb for multi-agent (M1-M6)
```

**Via CLI:**

```bash
# Run baseline experiments
uv run python scripts/run_experiment.py --config configs/experiments/baselines.yaml

# Run multi-agent experiments
uv run python scripts/run_experiment.py --config configs/experiments/multiagent.yaml

# Override model
uv run python scripts/run_experiment.py --config configs/experiments/baselines.yaml --model gpt-4.1
```

### Viewing Results

```bash
# Start the dashboard
cd dashboard
npm install
npm run dev
# Open http://localhost:3000
```

## Project Structure

```
agentic-ai-for-clm/
├── src/
│   ├── agents/              # Multi-agent system (LangGraph)
│   │   ├── orchestrator.py      # Category routing + workflow graph
│   │   ├── risk_liability.py    # Risk & Liability specialist (13 cats)
│   │   ├── temporal_renewal.py  # Temporal/Renewal specialist (11 cats)
│   │   ├── ip_commercial.py     # IP & Commercial specialist (17 cats)
│   │   ├── validation.py        # Grounding & format validation
│   │   ├── base.py              # BaseAgent, AgentConfig, ExtractionResult
│   │   ├── state.py             # LangGraph state definitions
│   │   └── checkpointing.py     # State persistence
│   ├── baselines/           # Single-agent baselines
│   │   ├── zero_shot.py         # B1: ContractEval replication
│   │   ├── chain_of_thought.py  # B4: CoT reasoning
│   │   └── combined_prompts.py  # M6: Combined specialist prompts
│   ├── evaluation/          # Metrics & statistics
│   │   ├── metrics.py           # F1, F2, Jaccard, laziness, grounding
│   │   └── statistical.py       # Bootstrap CI, McNemar, Wilcoxon, Cohen's d
│   ├── data/                # Dataset handling
│   │   └── cuad_loader.py       # CUAD loader + tier stratification
│   ├── models/              # LLM provider abstraction
│   │   ├── config.py            # Model registry (19 models)
│   │   ├── client.py            # Unified API for Anthropic/OpenAI/Google/Ollama
│   │   └── diagnostics.py       # Token/cost/latency tracking
│   └── prompts/             # Prompt management
│       └── registry.py          # YAML-based PromptRegistry
├── prompts/                 # YAML prompt templates
│   ├── baselines/               # B1, B4, M6 prompts
│   ├── specialists/             # Domain specialist prompts with indicators
│   └── system/                  # Common extraction instructions
├── configs/                 # Experiment configurations
│   └── experiments/             # baselines.yaml, multiagent.yaml
├── dashboard/               # Next.js visualization dashboard
│   └── src/                     # React components, API routes, data loaders
├── notebooks/               # Jupyter analysis notebooks
│   ├── 01_data_exploration.ipynb    # Dataset inspection
│   ├── 02_workflow_test.ipynb       # Single-run testing
│   ├── 03_baseline_calibration.ipynb  # B1, B4 calibration
│   └── 04_multiagent_experiment.ipynb # M1-M6 + statistical comparison
├── experiments/             # Output data
│   ├── results/                 # Summary JSON + intermediate JSONL
│   ├── diagnostics/             # Token/cost/latency per run
│   └── logs/                    # LangFuse exports
├── tests/                   # Test suite (81 tests)
├── scripts/                 # CLI runners
├── pyproject.toml           # Package config
└── CLAUDE.md                # Detailed project specification
```

## Experimental Configurations

| Config | Type | Description | Notebook |
|--------|------|-------------|----------|
| **B1** | Baseline | Zero-shot single-agent (ContractEval replication) | 03 |
| **B4** | Baseline | Chain-of-Thought single-agent | 03 |
| **M1** | Multi-Agent | Full system: orchestrator + 3 specialists + validation | 04 |
| **M6** | Ablation | Combined specialist prompts in single agent | 04 |
| M2--M5 | Ablations | Future ablation variants | 04 |

**Key comparison:** M1 vs M6 tests whether multi-agent *architecture* matters, or if the benefit comes from better *prompts* alone.

## Evaluation Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| **F2 Score** | > 0.73 | Recall-weighted F-score (primary metric) |
| **F2 (Rare)** | > 0.40 | Performance on hard categories |
| **Laziness Rate** | < 3% | False "no clause" responses |
| **Jaccard** | > 0.50 | Span overlap similarity |
| **Grounding Rate** | > 95% | Extracted text exists in source |
| **Trace Completeness** | > 90% | Auditable reasoning chain |

## Hypotheses

| ID | Hypothesis | Test |
|----|-----------|------|
| **H1** | Multi-agent beats single-agent baselines | M1 F2 > B1 F2 (p < 0.05) |
| **H2** | Specialists help rare categories most | dF2_rare > dF2_common |
| **H3** | Architecture matters, not just prompts | M1 > M6 (McNemar) |
| **H4** | Multi-agent produces auditable reasoning | Trace completeness > 90% |

## Models

19 LLMs evaluated across proprietary and open-source:

| Type | Models |
|------|--------|
| **Proprietary** | Claude Sonnet 4, GPT 4.1, GPT 4.1 Mini, Gemini 2.5 Pro |
| **DeepSeek** | R1 Distill Qwen 7B, R1 0528 Qwen3 8B |
| **LLaMA** | 3.1 8B Instruct |
| **Gemma** | 3 4B, 3 12B |
| **Qwen3** | 4B, 8B, 8B AWQ, 8B FP8, 14B (each with thinking/non-thinking) |

Open-source models run locally via [Ollama](https://ollama.com). AWQ/FP8 quantisation variants may require [vLLM](https://docs.vllm.ai).

## Dataset

Uses **CUAD** (Contract Understanding Atticus Dataset):

| Property | Value |
|----------|-------|
| Test contracts | 102 |
| Test samples | 4,128 |
| Categories | 41 clause types |
| Label split | 30% positive / 70% negative |
| Context length | 0.6k -- 301k characters |

Categories are stratified into **common** (F1 > 0.7), **moderate** (0.3--0.7), and **rare** (near-zero F1) tiers based on ContractEval benchmarks.

## Dashboard

The Next.js dashboard provides interactive visualization of experiment results:

- **Experiments List** -- search, filter by config type, sort by any metric, click to drill down
- **Experiment Detail** -- metrics overview, confusion matrix, classification distribution, per-tier breakdown
- **Samples Table** -- filter by tier/classification, agent routing column for M1 runs
- **Sample Detail** -- side-by-side ground truth vs prediction, contract text viewer, agent trace
- **Config View** -- system prompts (baselines), architecture details (M1: specialist prompts, routing table, workflow)
- **Diagnostics** -- token usage, cost breakdown, latency statistics

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Run linting
uv run ruff check src/

# Run type checking
uv run mypy src/

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# Start dashboard dev server
cd dashboard && npm run dev
```

## Statistical Methodology

Following Dror et al. (ACL 2018):

- **Bootstrap CI:** 1000 samples, 95% confidence intervals
- **Significance:** McNemar (paired binary), Wilcoxon (paired continuous)
- **Correction:** Benjamini-Hochberg for multiple comparisons
- **Effect size:** Cohen's d

## References

1. **ContractEval** (Liu et al., 2025) -- Primary baseline methodology
2. **CUAD** (Hendrycks et al., NeurIPS 2021) -- Dataset
3. **Dror et al.** (ACL 2018) -- Statistical testing framework
4. **MAST Taxonomy** (Cemri et al., 2025) -- Multi-agent failure modes
5. **Gao et al.** (2025) -- When multi-agent helps/hurts

## License

MIT
