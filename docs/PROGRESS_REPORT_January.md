# Progress Report: Multi-Agent Contract Analysis System

**Date:** January 2025
**Author:** Trung Nguyen
**Thesis:** Multi-Agent Systems for Contract Lifecycle Management

---

## Project Overview

Building a multi-agent system for contract clause extraction, evaluated on the CUAD dataset (510 contracts, 41 clause categories). The goal is to compare multi-agent architectures against single-agent baselines.

---

## Current Setup

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Orchestrator                         │
│                   (LangGraph Workflow)                   │
└─────────────┬──────────────┬──────────────┬─────────────┘
              │              │              │
              ▼              ▼              ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Risk/Liability │ │ Temporal/Renewal│ │  IP/Commercial  │
│   (13 cats)     │ │    (11 cats)    │ │    (17 cats)    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Tech Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | LangGraph (StateGraph) |
| LLM Provider | Anthropic Claude (primary), OpenAI (comparison) |
| Observability | Langfuse |
| Dataset | CUAD v1 (local JSON + HuggingFace) |
| Package Manager | uv |

---

## What's Implemented

### Data Layer
- **CUAD Loader**: Loads 20,910 Q&A pairs from local JSON or HuggingFace
- **Category Tiers**: Stratified into common/moderate/rare based on difficulty
- **Answer Spans**: Tracks all ~13,800 ground truth spans (not just first match)

### Agent Layer
- **3 Specialist Agents**: Each with domain-specific prompts and category indicators
- **Orchestrator**: Routes categories to appropriate specialist via LangGraph
- **Validation Agent**: Stub for grounding verification (not yet implemented)

### Prompt Management
- **YAML-based prompts**: Separated into `prompts/specialists/` and `prompts/baselines/`
- **Category indicators**: Per-category keyword lists for extraction guidance
- **Prompt registry**: Loads and formats prompts with variable interpolation

### Model Infrastructure
- **Multi-provider client**: Unified interface for Anthropic/OpenAI
- **Diagnostics tracking**: Token usage, costs, latency per call
- **Model registry**: Easy switching between claude-sonnet, claude-haiku, gpt-4o

### Baselines (Stubs)
- **B1 Zero-shot**: ContractEval replication (exact prompt)
- **B4 Chain-of-Thought**: Step-by-step reasoning
- **M6 Combined Prompts**: Ablation test (all specialist knowledge in one agent)

---

## Notebooks

| Notebook | Purpose |
|----------|---------|
| `01_data_exploration.ipynb` | Explore CUAD dataset statistics and samples |
| `02_workflow_test.ipynb` | Test multi-agent pipeline on 10 samples with Langfuse tracing |

---

## Next Steps

1. **Run baseline experiments** on full test set
2. **Implement validation agent** for grounding checks
3. **Add evaluation metrics** (F1, F2, Jaccard, laziness rate)
4. **Statistical analysis** (bootstrap CI, McNemar test)
5. **Compare M1 (multi-agent) vs baselines**

---

## Quick Start

```bash
# Install dependencies
uv sync

# Set API keys in .env
cp .env.example .env

# Test data loader
uv run python scripts/test_loader.py

# Run workflow test notebook
uv run jupyter notebook notebooks/02_workflow_test.ipynb
```
