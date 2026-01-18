# Multi-Agent Contract Analysis System

Master's thesis implementation investigating whether multi-agent architectures can improve contract clause extraction beyond single-agent LLM baselines.

**Author:** Trung Nguyen
**Institution:** TU München, Department of Informatics
**Supervisor:** Prof. Dr. Ingo Weber

## Research Question

> Can a multi-agent framework improve contract clause extraction accuracy beyond single-agent baselines while providing superior explainability?

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                      │
│       Routes queries to specialists by category     │
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

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run tests
pytest tests/ -v

# Run baseline experiment
python scripts/run_experiment.py --config configs/experiments/baselines.yaml

# Analyze results
python scripts/analyze_results.py --results experiments/results/
```

## Project Structure

```
contract-mas/
├── src/
│   ├── agents/           # Multi-agent system
│   │   ├── orchestrator.py
│   │   ├── risk_liability.py
│   │   ├── temporal_renewal.py
│   │   ├── ip_commercial.py
│   │   └── validation.py
│   ├── baselines/        # Baseline implementations
│   │   ├── zero_shot.py      # B1: ContractEval replication
│   │   ├── chain_of_thought.py   # B4: CoT baseline
│   │   └── combined_prompts.py   # M6: Critical ablation
│   ├── evaluation/       # Metrics and statistics
│   │   ├── metrics.py    # F1, F2, Jaccard, laziness
│   │   └── statistical.py    # Bootstrap CI, significance tests
│   └── data/             # CUAD data loading
│       └── cuad_loader.py
├── configs/
│   ├── prompts/          # Agent prompt configurations
│   └── experiments/      # Experiment configurations
├── scripts/              # Experiment runners
├── tests/                # Unit tests
└── experiments/          # Results and logs
```

## Experimental Configurations

| Config | Description | Purpose |
|--------|-------------|---------|
| **B1** | Zero-shot single-agent | ContractEval replication |
| **B4** | Chain-of-Thought | Reasoning baseline |
| **M1** | Full multi-agent system | Core contribution |
| **M6** | Combined prompts single-agent | Architecture vs prompting ablation |

## Evaluation Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| F2 Score | > 0.73 | Recall-weighted F-score |
| F2 (Rare) | > 0.40 | Performance on hard categories |
| Laziness Rate | < 3% | False "no clause" responses |
| Grounding Rate | > 95% | Extracted text found in source |

## Dataset

Uses CUAD (Contract Understanding Atticus Dataset):
- 102 test contracts
- 4,128 test samples
- 41 clause categories
- Stratified by difficulty: common, moderate, rare

## Key Hypotheses

1. **H1:** Multi-agent beats single-agent baselines (F2)
2. **H2:** Specialists help rare categories most
3. **H3:** Architecture matters, not just prompts (M1 > M6)
4. **H4:** Multi-agent produces auditable reasoning traces

## Development

```bash
# Linting
ruff check src/

# Type checking
mypy src/

# Run specific test
pytest tests/test_metrics.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## References

1. ContractEval (Liu et al., 2025) - Baseline methodology
2. CUAD (Hendrycks et al., NeurIPS 2021) - Dataset
3. Dror et al. (ACL 2018) - Statistical testing framework
