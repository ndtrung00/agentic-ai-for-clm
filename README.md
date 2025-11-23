# Multi-Agentic AI Systems for Contract Lifecycle Management (CLM)

Master's Thesis Project - Technical University of Munich 

**Author:** Trung Nguyen
**Supervisor:** Prof. Dr. Ingo Weber
**Advisor:** MS Samed Bayer
**Timeline:** October 2025 - April 2026

## Overview

This repository contains the implementation and evaluation of a multi-agent framework for Contract Lifecycle Management (CLM) systems. The project explores how specialized AI agents can improve contract analysis efficiency, accuracy, and explainability in enterprise environments.

## Research Questions

- How can a multi-agent framework be designed and implemented to improve contract analysis efficiency, accuracy, and explainability in enterprise CLM systems?
- What agent specialization patterns are most effective for contract analysis tasks?
- How does a multi-agent approach compare to single-agent systems?
- What explainability mechanisms are most effective for enterprise trust and transparency?

## Architecture

The system implements four key agent roles:

1. **Risk Analysis Agent** - Detects red-flag clauses, liability gaps, and unbalanced terms
2. **Clause Alignment Agent** - Ensures consistency across interrelated contracts
3. **Obligation Tracking Agent** - Monitors post-signature obligations and deadlines
4. **Dependency Graph Agent** - Maintains dynamic representation of clause relationships

## Technology Stack

- **Orchestration:** LangGraph for agent coordination
- **LLM Integration:** OpenAI GPT-4 / Anthropic Claude
- **Document Processing:** AWS Textract, custom OCR pipeline
- **Vector Database:** Supabase
- **Observability:** LangFuse for tracing and explainability
- **Language:** Python 3.11+

## Repository Structure

```
.
├── src/                    # Source code
│   ├── agents/            # Agent implementations
│   ├── core/              # Core framework code
│   ├── pipeline/          # Document processing pipeline
│   └── utils/             # Utility functions
├── configs/               # Configuration files (YAML/JSON)
├── data/                  # Datasets and test contracts
├── experiments/           # Experiment scripts and results
├── notebooks/             # Jupyter notebooks for analysis
├── tests/                 # Unit and integration tests
├── docs/                  # Documentation
└── thesis/                # Thesis writing materials
```

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Poetry or pip for dependency management
- AWS account (for Textract)
- Supabase account
- OpenAI API key or Anthropic API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd agentic-ai-for-clm

# Install dependencies
pip install -r requirements.txt
# or
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Quick Start

```bash
# Run the prototype
python src/main.py

# Run tests
pytest tests/

# Start Jupyter for analysis
jupyter notebook notebooks/
```

## Development Timeline

- **Phase 1 (Oct-Nov 2025):** Literature review and framework design
- **Phase 2 (Dec 2025-Jan 2026):** Prototype implementation
- **Phase 3 (Feb-Mar 2026):** Evaluation and validation
- **Thesis Writing:** Final 3-4 weeks (Mar-Apr 2026)

## Milestones

- [x] Repository setup
- [ ] Framework design complete
- [ ] Agent roles defined
- [ ] Working prototype with core functionality
- [ ] Evaluation complete
- [ ] Thesis writing finished

## Contributing

This is a thesis project. For questions or collaboration inquiries, please contact Trung Nguyen.

## License

[To be determined]

## Acknowledgments

- Department of Informatics, Technical University of Munich
- Prof. Dr. Ingo Weber (Supervisor)
- MS Samed Bayer (Advisor)
