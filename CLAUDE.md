# CLAUDE.md - Multi-Agent Contract Analysis System

## Project Overview

**Title:** Design and Evaluation of Multi-Agentic AI Systems for Contract Lifecycle Management
**Author:** Trung Nguyen
**Institution:** TU München, Department of Informatics
**Supervisor:** Prof. Dr. Ingo Weber
**Timeline:** October 2025 -- April 2026

This is a master's thesis implementation investigating whether multi-agent architectures can improve contract clause extraction beyond single-agent LLM baselines.

---

## Research Questions

**Main RQ:** Can a multi-agent framework improve contract clause extraction accuracy beyond single-agent baselines while providing superior explainability?

**Testable Hypotheses:**

| ID  | Hypothesis                               | Success Metric                         |
| --- | ---------------------------------------- | -------------------------------------- |
| H1  | Multi-agent beats single-agent baselines | F2_multiagent > F2_baseline (p < 0.05) |
| H2  | Specialists help rare categories most    | dF2_rare > dF2_common                  |
| H3  | Architecture matters, not just prompts   | M1 > M6 significantly                  |
| H4  | Multi-agent produces auditable reasoning | Trace completeness > 90%               |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                      │
│  Routes queries to specialists based on category    │
│  (LangGraph state machine)                          │
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
┌─────────────────────────────────────────────────────┐
│              VALIDATION LAYER                       │
│  Format check → Grounding verification → Confidence │
└─────────────────────────────────────────────────────┘
```

**Workflow:** route → specialist → validate → finalize

---

## Project Structure

```
agentic-ai-for-clm/
├── src/
│   ├── agents/
│   │   ├── __init__.py              # Public exports
│   │   ├── base.py                  # BaseAgent, AgentConfig, ExtractionResult
│   │   ├── state.py                 # GraphState, InputState, OutputState for LangGraph
│   │   ├── checkpointing.py         # Memory/SQLite checkpointing
│   │   ├── orchestrator.py          # LangGraph routing + CATEGORY_ROUTING map
│   │   ├── risk_liability.py        # 13 categories
│   │   ├── temporal_renewal.py      # 11 categories
│   │   ├── ip_commercial.py         # 17 categories
│   │   └── validation.py            # Grounding & format check
│   ├── baselines/
│   │   ├── __init__.py
│   │   ├── zero_shot.py             # B1: ContractEval replication
│   │   ├── chain_of_thought.py      # B4: CoT baseline
│   │   └── combined_prompts.py      # M6: Combined prompts ablation
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py               # F1, F2, Jaccard, laziness, grounding, batch eval
│   │   └── statistical.py           # Bootstrap CI, McNemar, Wilcoxon, BH, Cohen's d
│   ├── data/
│   │   ├── __init__.py
│   │   └── cuad_loader.py           # CUADDataLoader + tier stratification
│   ├── models/
│   │   ├── __init__.py
│   │   ├── config.py                # ModelConfig registry (19 models)
│   │   ├── client.py                # Unified invoke_model() for all providers
│   │   └── diagnostics.py           # Token/cost/latency tracking
│   └── prompts/
│       ├── __init__.py
│       └── registry.py              # YAML-based PromptRegistry + PromptTemplate
├── prompts/                         # YAML prompt templates
│   ├── baselines/
│   │   ├── zero_shot.yaml           # B1 prompt (exact ContractEval match)
│   │   ├── chain_of_thought.yaml    # B4 prompt
│   │   └── combined_prompts.yaml    # M6 combined specialist prompt
│   ├── specialists/
│   │   ├── risk_liability.yaml      # 13 categories + domain indicators
│   │   ├── temporal_renewal.yaml    # 11 categories + domain indicators
│   │   └── ip_commercial.yaml       # 17 categories + domain indicators
│   └── system/
│       └── extraction_base.yaml     # Common anti-laziness + structured output
├── configs/
│   ├── experiments/
│   │   ├── baselines.yaml           # B1, B4 config with calibration targets
│   │   └── multiagent.yaml          # M1, M6 config with success criteria
│   └── prompts/                     # Legacy prompt references
│       ├── orchestrator.yaml
│       ├── risk_liability.yaml
│       ├── temporal_renewal.yaml
│       └── ip_commercial.yaml
├── dashboard/                       # Next.js experiment visualization
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Landing page
│   │   │   ├── layout.tsx           # Root layout with sidebar
│   │   │   ├── experiments/
│   │   │   │   ├── page.tsx         # Experiments list (server)
│   │   │   │   ├── experiments-table.tsx  # Interactive table (client)
│   │   │   │   └── [runId]/
│   │   │   │       ├── page.tsx     # Experiment detail
│   │   │   │       ├── tabs.tsx     # Overview/Samples/Diagnostics/Config tabs
│   │   │   │       └── samples/
│   │   │   │           └── [sampleId]/
│   │   │   │               └── page.tsx  # Sample detail with contract viewer
│   │   │   └── api/
│   │   │       └── experiments/     # REST API routes
│   │   ├── components/
│   │   │   ├── metrics/             # MetricCard, MetricsGrid, ConfusionMatrix, TierBreakdown
│   │   │   ├── charts/             # ClassificationPie (recharts)
│   │   │   ├── samples/            # SamplesTable, ClassificationBadge, ContractViewer
│   │   │   ├── diagnostics/        # DiagnosticsCards (tokens, cost, latency)
│   │   │   ├── layout/             # Sidebar navigation
│   │   │   └── ui/                 # shadcn/ui primitives
│   │   └── lib/
│   │       ├── types.ts            # TypeScript interfaces (mirrors Python types)
│   │       ├── data-loader.ts      # Reads experiment JSON/JSONL from filesystem
│   │       ├── format.ts           # Number/date/currency formatters
│   │       ├── colors.ts           # Chart color schemes
│   │       └── utils.ts            # General utilities
│   └── package.json                # Next.js 16, React 19, Recharts, shadcn/ui
├── experiments/
│   ├── results/                     # Summary JSON + intermediate JSONL per run
│   ├── diagnostics/                 # Token/cost/latency diagnostics per run
│   └── logs/                        # LangFuse export backups
├── tests/
│   ├── test_metrics.py              # 30+ tests for F1/F2/Jaccard/laziness/grounding
│   ├── test_data_loader.py          # CUAD loading, parsing, tier stratification
│   ├── test_agents.py               # Agent init, extraction flow, orchestration
│   └── test_statistical.py          # Bootstrap CI, McNemar, Wilcoxon, BH, Cohen's d
├── notebooks/
│   ├── 01_data_exploration.ipynb    # CUAD dataset inspection
│   ├── 02_workflow_test.ipynb       # Single baseline test with diagnostics
│   ├── 03_baseline_calibration.ipynb  # B1, B4 calibration runs
│   └── 04_multiagent_experiment.ipynb # M1-M6 experiments + statistical comparison
├── scripts/
│   ├── run_experiment.py            # CLI experiment runner (B1/B4/M1/M6)
│   ├── analyze_results.py           # Post-hoc analysis
│   └── test_loader.py              # Quick CUAD loader test
├── data/
│   └── cuad/                        # Local CUAD dataset cache
├── docs/                            # Documentation
├── pyproject.toml                   # Python package config (uv)
├── uv.lock                          # Locked dependencies
├── .env.example                     # Environment template
├── README.md                        # Project overview
├── PROGRESS.md                      # Implementation progress tracker
└── CLAUDE.md                        # This file
```

---

## Technical Stack

| Component             | Technology                        | Purpose                                      |
| --------------------- | --------------------------------- | -------------------------------------------- |
| Package manager       | uv                                | Fast Python package management               |
| Multi-agent framework | LangGraph                         | Graph-based state machines, workflow control  |
| Observability         | LangFuse                          | Reasoning traces, experiment tracking         |
| LLM Providers         | Anthropic, OpenAI, Google, Ollama | See model list below                         |
| Data                  | HuggingFace datasets              | CUAD loading                                 |
| Statistics            | scipy, numpy                      | Bootstrap CI, significance tests             |
| Dashboard             | Next.js 16, React 19, Recharts    | Experiment visualization & analysis          |
| UI Components         | shadcn/ui, Tailwind CSS 4         | Dashboard component library                  |

### Python Dependencies

**Core:**
- `langgraph>=0.2.0` -- Multi-agent orchestration
- `langchain>=0.3.0`, `langchain-anthropic>=0.3.0` -- LLM framework
- `langfuse>=2.0.0` -- Observability
- `anthropic>=0.40.0` -- Anthropic SDK
- `datasets>=3.0.0` -- HuggingFace CUAD loading
- `pydantic>=2.0.0` -- Data validation
- `pyyaml>=6.0` -- Prompt/config parsing
- `scipy>=1.14.0`, `numpy>=2.0.0`, `pandas>=2.2.0` -- Statistics
- `tenacity>=9.0.0` -- API retry logic
- `tqdm>=4.66.0` -- Progress bars

**Dev:** `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, `jupyter`

### Dashboard Dependencies

- `next@16.1.6`, `react@19.2.3` -- Framework
- `recharts@3.7.0` -- Charts
- `radix-ui`, `class-variance-authority`, `tailwind-merge` -- UI
- `shadcn` -- Component generator
- `tailwindcss@4` -- Styling

### Evaluated Models

19 LLMs across proprietary and open-source:

**Proprietary (4):**

| Key               | Model                  | Provider  |
| ----------------- | ---------------------- | --------- |
| `claude-sonnet-4` | Claude Sonnet 4        | Anthropic |
| `gpt-4.1`         | GPT 4.1                | OpenAI    |
| `gpt-4.1-mini`    | GPT 4.1 Mini           | OpenAI    |
| `gemini-2.5-pro`  | Gemini 2.5 Pro Preview | Google    |

**Open-source via Ollama (15):**

| Key                                      | Model                       |
| ---------------------------------------- | --------------------------- |
| `deepseek-r1-distill-qwen-7b`            | DeepSeek R1 Distill Qwen 7B |
| `deepseek-r1-0528-qwen3-8b`              | DeepSeek R1 0528 Qwen3 8B   |
| `llama-3.1-8b`                           | LLaMA 3.1 8B Instruct       |
| `gemma-3-4b`                             | Gemma 3 4B                  |
| `gemma-3-12b`                            | Gemma 3 12B                 |
| `qwen3-4b` / `qwen3-4b-thinking`         | Qwen3 4B                    |
| `qwen3-8b` / `qwen3-8b-thinking`         | Qwen3 8B                    |
| `qwen3-8b-awq` / `qwen3-8b-awq-thinking` | Qwen3 8B AWQ                |
| `qwen3-8b-fp8` / `qwen3-8b-fp8-thinking` | Qwen3 8B FP8                |
| `qwen3-14b` / `qwen3-14b-thinking`       | Qwen3 14B                   |

Qwen3 "thinking" variants use `/think` tag for reasoning. AWQ/FP8 may require vLLM.

---

## Dataset: CUAD

**Source:** `datasets.load_dataset("theatticusproject/cuad-qa")`

| Metric             | Value                       |
| ------------------ | --------------------------- |
| Test contracts     | 102                         |
| Test data points   | 4,128                       |
| Categories         | 41 clause types             |
| Label distribution | 30% positive / 70% negative |
| Context length     | 0.6k -- 301k characters     |

### Category Stratification (by ContractEval F1)

**Common (F1 > 0.7):** Governing Law, Parties, Agreement Date, Effective Date, Expiration Date, Document Name

**Moderate (0.3--0.7):** Renewal Term, License Grant, Termination for Convenience, Anti-Assignment, Change of Control, etc.

**Rare (near-zero F1):** Uncapped Liability, Joint IP Ownership, Notice Period to Terminate Renewal, Volume Restriction, etc.

---

## Agent-Category Mapping

### Risk & Liability Specialist (13 categories)

Uncapped Liability, Cap on Liability, Liquidated Damages, Insurance, Warranty Duration, Audit Rights, Non-Disparagement, Covenant Not to Sue, Third Party Beneficiary, Most Favored Nation, Change of Control, Post-Termination Services, Minimum Commitment

### Temporal/Renewal Specialist (11 categories)

Document Name, Parties, Agreement Date, Effective Date, Expiration Date, Renewal Term, Notice Period to Terminate Renewal, Termination for Convenience, Anti-Assignment, ROFR/ROFO/ROFN, Governing Law

### IP & Commercial Specialist (17 categories)

IP Ownership Assignment, Joint IP Ownership, License Grant, Non-Transferable License, Affiliate License-Licensor, Affiliate License-Licensee, Unlimited/All-You-Can-Eat License, Irrevocable or Perpetual License, Source Code Escrow, Exclusivity, Non-Compete, No-Solicit of Customers, No-Solicit of Employees, Competitive Restriction Exception, Revenue/Profit Sharing, Price Restrictions, Volume Restriction

---

## Experimental Configurations

### Baselines (notebook 03)

| Config | Type                | Description                                       |
| ------ | ------------------- | ------------------------------------------------- |
| **B1** | `zero_shot`         | Zero-shot single-agent (ContractEval replication)  |
| **B4** | `chain_of_thought`  | Chain-of-Thought single-agent                     |

### Multi-Agent (notebook 04)

| Config | Type                | Description                                             |
| ------ | ------------------- | ------------------------------------------------------- |
| **M1** | `multiagent`        | Full system (orchestrator + 3 specialists + validation) |
| **M6** | `combined_prompts`  | Combined prompts single-agent (architecture ablation)   |
| M2--M5 | Various ablations   | Not yet implemented                                     |

**Key insight:** If M1 ~ M6, multi-agent overhead not justified. If M1 > M6, architecture provides genuine benefit.

---

## Evaluation Metrics

### Primary Metrics

| Metric                 | Formula                          | Target                     |
| ---------------------- | -------------------------------- | -------------------------- |
| **F2 Score**           | 5 * (P * R) / (4P + R)           | > 0.73 (vs 0.68 baseline)  |
| **F2 Rare Categories** | F2 on rare tier only             | > 0.40 (vs ~0.15 baseline) |
| **Laziness Rate**      | FN("no clause") / Total Positive | < 3% (vs ~10% baseline)    |
| **Jaccard Similarity** | |A n B| / |A u B|                | > 0.50                     |

### Explainability Metrics

| Metric             | Target |
| ------------------ | ------ |
| Trace Completeness | > 90%  |
| Grounding Rate     | > 95%  |

### TP/FP/FN Definitions (from ContractEval)

- **TP:** Label not empty AND prediction fully covers labeled span
- **TN:** Label empty AND model predicts "no related clause"
- **FP:** Label empty BUT model predicts non-empty clause
- **FN:** Label not empty BUT model outputs "no related clause" OR fails to cover span

---

## Output Formats

### Summary JSON (per run)

Saved to `experiments/results/{type}_{model}_{timestamp}_summary.json`. Contains:
- `config`: model_key, model_id, provider, baseline_type/experiment_type, temperature, max_tokens, samples_per_tier
- `prompt` (baselines): system_prompt text
- `architecture` (M1): specialist_prompts, routing_table, workflow, validation_enabled
- `metrics`: precision, recall, f1, f2, avg_jaccard, laziness_rate, tp/fp/fn/tn
- `per_tier`: per-tier breakdown (common/moderate/rare)
- `samples[]`: id, category, tier, classification, jaccard, grounding_rate
- `diagnostics`: token counts, cost, latency

### Intermediate JSONL (per run, crash-safe)

One line per sample in `experiments/results/{type}_{model}_{timestamp}_intermediate.jsonl`. Contains full input/output/evaluation per sample for detailed analysis and dashboard drill-down.

### Diagnostics JSON (per run)

Saved to `experiments/diagnostics/`. Contains by-model and by-agent breakdowns of token usage, costs, and latencies.

---

## Dashboard

The Next.js dashboard reads experiment results directly from `experiments/results/` and provides:

### Pages

1. **Experiments List** (`/experiments`) -- searchable, filterable, sortable table of all runs
2. **Experiment Detail** (`/experiments/[runId]`) -- tabbed view:
   - **Overview**: MetricsGrid, ConfusionMatrix, ClassificationPie, TierBreakdown
   - **Samples**: filterable table with tier/classification filters, agent routing column (M1)
   - **Diagnostics**: token usage, cost, latency cards
   - **Config**: system prompt (baselines), architecture view (M1 with specialist prompts, routing table, workflow), model parameters
3. **Sample Detail** (`/experiments/[runId]/samples/[sampleId]`) -- ground truth vs prediction comparison, contract viewer with clause highlighting, usage details, agent trace (M1)

### Key Features

- Handles both baseline (`baseline_type`) and multi-agent (`experiment_type`) result formats
- Clickable rows throughout for drill-down navigation
- Agent routing column in samples table for M1 runs
- Architecture visualization showing LangGraph workflow and specialist details
- Server components for data loading, client components for interactivity

### Running the Dashboard

```bash
cd dashboard
npm install
npm run dev          # Development at http://localhost:3000
npm run build        # Production build
```

---

## Baseline Calibration Targets

From ContractEval paper (GPT-4.1):

- F1: 0.641
- F2: 0.678
- Jaccard: 0.472
- False "no related clause" rate: 7.1%

**Action:** If B1 differs significantly from these numbers, investigate prompt/parsing differences before proceeding.

---

## Statistical Methodology

Following Dror et al. (ACL 2018):

1. **Bootstrap Confidence Intervals:** 1000 samples, 95% CI
2. **Significance Tests:** McNemar (paired binary), Wilcoxon (paired continuous)
3. **Multiple Comparison Correction:** Benjamini-Hochberg
4. **Effect Size:** Cohen's d (0.2=small, 0.5=medium, 0.8=large)

**Reporting template:**

```
Performance: 87.3% F2 (95% CI: 85.1-89.5)
Comparison: +3.2% vs. baseline (p < 0.001, Cohen's d = 0.65)
```

All statistical functions are implemented in `src/evaluation/statistical.py` with exports: `bootstrap_ci`, `mcnemar_test`, `wilcoxon_test`, `benjamini_hochberg`, `cohens_d`.

---

## Key Problems We're Addressing

### 1. Laziness Problem

- **Issue:** Models respond "No related clause" when clauses exist (up to 30% false negative rate)
- **Solution:** Verification layer double-checks negative responses; anti-laziness prompting in specialist YAML templates

### 2. Rare Category Failure

- **Issue:** Near-zero F1 on Uncapped Liability, Joint IP Ownership, etc.
- **Solution:** Dedicated specialist with category-specific indicators and pattern libraries (defined in `prompts/specialists/*.yaml`)

### 3. Explainability Gap

- **Issue:** Single-agent provides no decomposed reasoning
- **Solution:** Structured traces logged via LangFuse at every decision point; LangGraph state machine captures node traversal

---

## ContractEval Baseline Prompt (MUST REPLICATE EXACTLY)

```
You are an assistant with strong legal knowledge, supporting senior lawyers by preparing reference materials. Given a Context and a Question, extract and return only the sentence(s) from the Context that directly address or relate to the Question. Do not rephrase or summarize in any way--respond with exact sentences from the Context relevant to the Question. If a relevant sentence contains unrelated elements such as page numbers or whitespace, include them exactly as they appear. If no part of the Context is relevant to the Question, respond with: "No related clause."
```

This prompt is stored in `prompts/baselines/zero_shot.yaml` and loaded via `PromptRegistry`.

---

## Prompt Design Principles

### Anti-Laziness Instructions

```
IMPORTANT: If you are uncertain whether a clause is relevant, INCLUDE IT.
It is better to extract a potentially relevant clause than to miss one.
Only respond "No related clause" if you have thoroughly searched and found nothing.
```

### Structured Output Format

```json
{
  "extracted_clauses": ["exact text from contract"],
  "reasoning": "Step-by-step explanation of extraction logic",
  "confidence": 0.85,
  "category_indicators_found": ["cap", "limitation", "$X million"]
}
```

### Specialist Framing

Each specialist prompt (in `prompts/specialists/*.yaml`) includes:

1. Domain expertise declaration
2. Category-specific indicators to look for
3. Common patterns and variations
4. Anti-laziness reminder
5. Structured output requirements

---

## Development Commands

```bash
# Install dependencies (with dev extras)
uv sync --all-extras

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Run tests (81 tests)
uv run pytest tests/ -v

# Run linting
uv run ruff check src/

# Run type checking
uv run mypy src/

# Run experiment via CLI
uv run python scripts/run_experiment.py --config configs/experiments/baselines.yaml
uv run python scripts/run_experiment.py --config configs/experiments/multiagent.yaml --model claude-sonnet-4-20250514

# Run dashboard
cd dashboard && npm run dev

# Build dashboard
cd dashboard && npm run build
```

---

## Environment Variables

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...                       # or GOOGLE_API_KEY
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com
DEFAULT_MODEL=claude-sonnet-4-20250514
```

---

## Risk Mitigation

### If multi-agent doesn't beat baselines:

1. Thesis framed as "empirical investigation," not proof of superiority
2. M6 ablation isolates architecture vs. prompting benefit
3. Valid contribution: "When does multi-agent help?" with honest negative results
4. Explainability benefits may justify overhead even without accuracy gains

### Timeline risk mitigation:

- Minimum viable scope: B1, B4, M1, M6 only
- Cut M2--M5 ablations if needed
- Maintain statistical rigor regardless of scope

---

## Key References

1. **ContractEval** (Liu et al., 2025) -- Primary baseline methodology
2. **CUAD** (Hendrycks et al., NeurIPS 2021) -- Dataset
3. **Dror et al.** (ACL 2018) -- Statistical testing framework
4. **MAST Taxonomy** (Cemri et al., 2025) -- Multi-agent failure modes
5. **Gao et al.** (2025) -- When multi-agent helps/hurts

---

## Notes for Claude Code

- Always use type hints
- Add docstrings to all public functions
- Log to LangFuse with `@observe()` decorator
- Keep prompts in YAML, not hardcoded -- use `PromptRegistry` from `src/prompts/registry.py`
- Write unit tests for metrics (test suite: 81 tests)
- Use structured outputs (JSON) for parsing reliability
- Handle long contracts (>100k chars) gracefully
- Use async where possible for LLM calls
- Notebook 03 is for baselines (B1, B4) only -- do not add M-variants
- Notebook 04 handles all M-variants (M1--M6) and statistical comparison
- Dashboard reads from `experiments/results/` -- summary JSON must include `config`, `metrics`, `samples[]`
- For M1 results, include `architecture` dict in summary JSON (specialist_prompts, routing_table, workflow)
- Experiment results use either `baseline_type`/`baseline_label` (notebooks 03) or `experiment_type`/`experiment_label` (notebook 04) -- dashboard handles both via fallback
