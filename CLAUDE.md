# CLAUDE.md - Multi-Agent Contract Analysis System

## Project Overview

**Title:** Design and Evaluation of Multi-Agentic AI Systems for Contract Lifecycle Management
**Author:** Trung Nguyen
**Institution:** TU München, Department of Informatics
**Supervisor:** Prof. Dr. Ingo Weber
**Timeline:** October 2025 – April 2026

This is a master's thesis implementation investigating whether multi-agent architectures can improve contract clause extraction beyond single-agent LLM baselines.

---

## Research Questions

**Main RQ:** Can a multi-agent framework improve contract clause extraction accuracy beyond single-agent baselines while providing superior explainability?

**Testable Hypotheses:**

| ID  | Hypothesis                               | Success Metric                         |
| --- | ---------------------------------------- | -------------------------------------- |
| H1  | Multi-agent beats single-agent baselines | F2_multiagent > F2_baseline (p < 0.05) |
| H2  | Specialists help rare categories most    | ΔF2_rare > ΔF2_common                  |
| H3  | Architecture matters, not just prompts   | M1 > M6 significantly                  |
| H4  | Multi-agent produces auditable reasoning | Trace completeness > 90%               |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                      │
│  Routes queries to specialists based on category    │
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

---

## Project Structure

```
contract-mas/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py          # LangGraph routing logic
│   │   ├── risk_liability.py        # 13 categories
│   │   ├── temporal_renewal.py      # 11 categories
│   │   ├── ip_commercial.py         # 17 categories
│   │   └── validation.py            # Grounding & format check
│   ├── baselines/
│   │   ├── __init__.py
│   │   ├── zero_shot.py             # B1: ContractEval replication
│   │   ├── chain_of_thought.py      # B4: CoT baseline
│   │   └── combined_prompts.py      # M6: Critical ablation
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── metrics.py               # F2, Jaccard, laziness rate
│   │   └── statistical.py           # Bootstrap CI, significance tests
│   ├── data/
│   │   ├── __init__.py
│   │   ├── cuad_loader.py           # CUAD dataset handling
│   │   └── category_mapping.py      # Agent-category assignments
│   └── config/
│       ├── prompts/                 # YAML prompt templates
│       │   ├── orchestrator.yaml
│       │   ├── risk_liability.yaml
│       │   ├── temporal_renewal.yaml
│       │   └── ip_commercial.yaml
│       └── experiments/             # Experiment configurations
│           ├── baselines.yaml
│           └── multiagent.yaml
├── experiments/
│   ├── results/                     # JSON outputs per run
│   └── logs/                        # LangFuse export backups
├── tests/
│   ├── test_metrics.py
│   ├── test_data_loader.py
│   └── test_agents.py
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_workflow_test.ipynb
│   ├── 03_baseline_calibration.ipynb    # B1, B4
│   └── 04_multiagent_experiment.ipynb   # M1–M6 + statistical comparison
├── scripts/
│   ├── run_experiment.py            # Main experiment runner
│   └── analyze_results.py           # Post-hoc analysis
├── pyproject.toml
├── uv.lock                          # Locked dependencies (commit to git)
├── .env.example
├── .gitignore
├── README.md
└── CLAUDE.md                        # This file
```

---

## Technical Stack

| Component             | Technology                        | Purpose                                      |
| --------------------- | --------------------------------- | -------------------------------------------- |
| Package manager       | uv                                | Fast Python package management               |
| Multi-agent framework | LangGraph                         | Graph-based state machines, workflow control |
| Observability         | LangFuse                          | Reasoning traces, experiment tracking        |
| LLM Providers         | Anthropic, OpenAI, Google, Ollama | See model list below                         |
| Data                  | HuggingFace datasets              | CUAD loading                                 |
| Statistics            | scipy, numpy                      | Bootstrap CI, significance tests             |

### Evaluated Models (from ContractEval)

19 LLMs evaluated across proprietary and open-source:

**Proprietary (4):**

| Key               | Model                  | Provider  | At exposure |
| ----------------- | ---------------------- | --------- | ----------- |
| `claude-sonnet-4` | Claude Sonnet 4        | Anthropic | x           |
| `gpt-4.1`         | GPT 4.1                | OpenAI    |             |
| `gpt-4.1-mini`    | GPT 4.1 Mini           | OpenAI    |             |
| `gemini-2.5-pro`  | Gemini 2.5 Pro Preview | Google    |             |

**Open-source via Ollama (15):**

| Key                                      | Model                       | At exposure |
| ---------------------------------------- | --------------------------- | ----------- |
| `deepseek-r1-distill-qwen-7b`            | DeepSeek R1 Distill Qwen 7B |             |
| `deepseek-r1-0528-qwen3-8b`              | DeepSeek R1 0528 Qwen3 8B   |             |
| `llama-3.1-8b`                           | LLaMA 3.1 8B Instruct       |             |
| `gemma-3-4b`                             | Gemma 3 4B                  |             |
| `gemma-3-12b`                            | Gemma 3 12B                 |             |
| `qwen3-4b` / `qwen3-4b-thinking`         | Qwen3 4B                    | x           |
| `qwen3-8b` / `qwen3-8b-thinking`         | Qwen3 8B                    | x           |
| `qwen3-8b-awq` / `qwen3-8b-awq-thinking` | Qwen3 8B AWQ                |             |
| `qwen3-8b-fp8` / `qwen3-8b-fp8-thinking` | Qwen3 8B FP8                |             |
| `qwen3-14b` / `qwen3-14b-thinking`       | Qwen3 14B                   |             |

Qwen3 "thinking" variants use the same model but with reasoning enabled via `/think` tag (vs `/no_think` for non-thinking). AWQ/FP8 quantisation variants may require vLLM serving instead of Ollama.

---

## Dataset: CUAD

**Source:** `datasets.load_dataset("theatticusproject/cuad-qa")`

| Metric             | Value                       |
| ------------------ | --------------------------- |
| Test contracts     | 102                         |
| Test data points   | 4,128                       |
| Categories         | 41 clause types             |
| Label distribution | 30% positive / 70% negative |
| Context length     | 0.6k - 301k characters      |

### Category Stratification (by ContractEval F1)

**Common (F1 > 0.7):** Governing Law, Parties, Agreement Date, Effective Date, Expiration Date, Document Name

**Moderate (0.3-0.7):** Renewal Term, License Grant, Termination for Convenience, Anti-Assignment, Change of Control, etc.

**Rare (near-zero F1):** Uncapped Liability, Joint IP Ownership, Notice Period to Terminate Renewal, Volume Restriction, etc.

---

## Agent-Category Mapping

### Risk & Liability Specialist (13 categories)

- Uncapped Liability
- Cap on Liability
- Liquidated Damages
- Insurance
- Warranty Duration
- Audit Rights
- Non-Disparagement
- Covenant Not to Sue
- Third Party Beneficiary
- Most Favored Nation
- Change of Control
- Post-Termination Services
- Minimum Commitment

### Temporal/Renewal Specialist (11 categories)

- Document Name
- Parties
- Agreement Date
- Effective Date
- Expiration Date
- Renewal Term
- Notice Period to Terminate Renewal
- Termination for Convenience
- Anti-Assignment
- ROFR/ROFO/ROFN
- Governing Law

### IP & Commercial Specialist (17 categories)

- IP Ownership Assignment
- Joint IP Ownership
- License Grant
- Non-Transferable License
- Affiliate License-Licensor
- Affiliate License-Licensee
- Unlimited/All-You-Can-Eat License
- Irrevocable or Perpetual License
- Source Code Escrow
- Exclusivity
- Non-Compete
- No-Solicit of Customers
- No-Solicit of Employees
- Competitive Restriction Exception
- Revenue/Profit Sharing
- Price Restrictions
- Volume Restriction

---

## Experimental Configurations

### Baselines

| Config | Description                                       |
| ------ | ------------------------------------------------- |
| **B1** | Zero-shot single-agent (ContractEval replication) |
| **B4** | Chain-of-Thought single-agent                     |

### Multi-Agent

| Config | Description                                             | Tests                                   |
| ------ | ------------------------------------------------------- | --------------------------------------- |
| **M1** | Full system (orchestrator + 3 specialists + validation) | Core contribution                       |
| **M6** | Combined prompts single-agent                           | **CRITICAL:** Architecture vs prompting |

**Key insight:** If M1 ≈ M6, multi-agent overhead not justified. If M1 > M6, architecture provides genuine benefit.

---

## Evaluation Metrics

### Primary Metrics

| Metric                 | Formula                          | Target                     |
| ---------------------- | -------------------------------- | -------------------------- |
| **F2 Score**           | 5 × (P × R) / (4P + R)           | > 0.73 (vs 0.68 baseline)  |
| **F2 Rare Categories** | F2 on rare tier only             | > 0.40 (vs ~0.15 baseline) |
| **Laziness Rate**      | FN("no clause") / Total Positive | < 3% (vs ~10% baseline)    |
| **Jaccard Similarity** | \|A ∩ B\| / \|A ∪ B\|            | > 0.50                     |

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

---

## Key Problems We're Addressing

### 1. Laziness Problem

- **Issue:** Models respond "No related clause" when clauses exist (up to 30% false negative rate)
- **Solution:** Verification layer double-checks negative responses; anti-laziness prompting

### 2. Rare Category Failure

- **Issue:** Near-zero F1 on Uncapped Liability, Joint IP Ownership, etc.
- **Solution:** Dedicated specialist with category-specific indicators and pattern libraries

### 3. Explainability Gap

- **Issue:** Single-agent provides no decomposed reasoning
- **Solution:** Structured traces logged via LangFuse at every decision point

---

## ContractEval Baseline Prompt (MUST REPLICATE EXACTLY)

```
You are an assistant with strong legal knowledge, supporting senior lawyers by preparing reference materials. Given a Context and a Question, extract and return only the sentence(s) from the Context that directly address or relate to the Question. Do not rephrase or summarize in any way—respond with exact sentences from the Context relevant to the Question. If a relevant sentence contains unrelated elements such as page numbers or whitespace, include them exactly as they appear. If no part of the Context is relevant to the Question, respond with: "No related clause."
```

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

Each specialist prompt includes:

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

# Run linting
uv run ruff check src/

# Run type checking
uv run mypy src/

# Run tests
uv run pytest tests/ -v

# Run single experiment
uv run python scripts/run_experiment.py --config experiments/baselines.yaml --model claude-sonnet-4-20250514

# Analyze results
uv run python scripts/analyze_results.py --results experiments/results/
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
```

---

## Sprint Timeline

| Sprint | Days  | Focus                                                    |
| ------ | ----- | -------------------------------------------------------- |
| S0     | 1-2   | Environment setup, repo structure                        |
| S1     | 3-7   | Data loader, baselines (B1, B4), metrics                 |
| S2     | 8-14  | Multi-agent core (orchestrator, specialists, validation) |
| S3     | 15-21 | M6 ablation, full experiments                            |
| S4     | 22-28 | Analysis, statistical validation, documentation          |

---

## Risk Mitigation

### If multi-agent doesn't beat baselines:

1. Thesis framed as "empirical investigation," not proof of superiority
2. M6 ablation isolates architecture vs. prompting benefit
3. Valid contribution: "When does multi-agent help?" with honest negative results
4. Explainability benefits may justify overhead even without accuracy gains

### Timeline risk mitigation:

- Minimum viable scope: B1, B4, M1, M6 only
- Cut M2-M5 ablations if needed
- Maintain statistical rigor regardless of scope

---

## Key References

1. **ContractEval** (Liu et al., 2025) - Primary baseline methodology
2. **CUAD** (Hendrycks et al., NeurIPS 2021) - Dataset
3. **Dror et al.** (ACL 2018) - Statistical testing framework
4. **MAST Taxonomy** (Cemri et al., 2025) - Multi-agent failure modes
5. **Gao et al.** (2025) - When multi-agent helps/hurts

---

## Notes for Claude Code

- Always use type hints
- Add docstrings to all public functions
- Log to LangFuse with `@observe()` decorator
- Keep prompts in YAML, not hardcoded
- Write unit tests for metrics
- Use structured outputs (JSON) for parsing reliability
- Handle long contracts (>100k tokens) gracefully
- Use async where possible for LLM calls
