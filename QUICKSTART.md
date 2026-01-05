# Quick Start Guide

Get your Multi-Agent CLM System up and running in 5 minutes.

## Prerequisites

- Python 3.11+ installed
- Git installed
- Code editor (VS Code recommended)

## Installation (5 minutes)

### Step 1: Navigate to Project

```bash
cd /Users/trungnguyen/Documents/@tum/study/Thesis/agentic-ai-for-clm
```

### Step 2: Set Up Python Environment

**Option A: Using venv (Recommended for quick start)**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Option B: Using Poetry (Recommended for development)**

```bash
# Install Poetry first if you haven't
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
poetry shell
```

### Step 3: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys (minimum required):

```bash
# At minimum, add one of these:
OPENAI_API_KEY=sk-your-key-here
# or
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Step 4: Verify Installation

```bash
# Run tests to verify setup
pytest tests/unit/ -v

# Or use make
make test-fast
```

## Quick Test Run

### Option 1: Run the Demo Application

```bash
python src/main.py
```

This will analyze a sample contract using all four agents.

### Option 2: Use Jupyter Notebook

```bash
jupyter notebook notebooks/01_getting_started.ipynb
```

### Option 3: Interactive Python

```python
from src.agents import RiskAnalysisAgent
from src.agents.base import AgentInput

# Create agent
agent = RiskAnalysisAgent()

# Prepare input
contract_text = """
SERVICES AGREEMENT
This agreement is between Company A and Company B...
"""

input_data = AgentInput(
    contract_text=contract_text,
    metadata={"contract_id": "TEST-001"}
)

# Run analysis (async)
import asyncio
result = asyncio.run(agent.analyze(input_data))
print(result)
```

## What's Working Now?

✅ **Fully Functional:**

- Project structure and organization
- Configuration system
- Agent base classes and interfaces
- Unit test framework
- Documentation

⚠️ **Placeholder Implementation:**

- Agent analysis logic (returns mock data)
- LLM integration (not yet connected)
- Vector database (not yet connected)
- Document processing pipeline

## Next Steps

### For Development:

1. Read `docs/ARCHITECTURE.md` to understand the system
2. Read `docs/SETUP.md` for detailed setup instructions
3. Check `PROJECT_STATUS.md` for current status and roadmap
4. Review the code in `src/agents/` to understand agent structure

### To Start Implementing:

1. Set up Supabase account and vector database (see `docs/SETUP.md`)
2. Set up AWS Textract (optional, for OCR)
3. Set up LangFuse (optional, for observability)
4. Implement actual LLM calls in agent `analyze()` methods

### Phase 1 Tasks (October-November 2025):

- [ ] Review literature on multi-agent systems
- [ ] Finalize agent architecture design
- [ ] Set up all external services (Supabase, AWS, etc.)
- [ ] Download and prepare CUAD dataset

## Common Commands

```bash
# Run application
make run
# or
python src/main.py

# Run tests
make test        # Full test suite with coverage
make test-fast   # Quick tests without coverage

# Code quality
make format      # Format code with Black
make lint        # Run linting with Ruff
make check       # Format, lint, and test

# Development
make notebook    # Start Jupyter
make clean       # Clean generated files

# Help
make help        # Show all available commands
```

## Project Structure Overview

```
agentic-ai-for-clm/
├── src/                    # Source code
│   ├── agents/            # Four specialized agents
│   ├── core/              # Configuration and core logic
│   └── main.py            # Entry point
├── tests/                 # Test suite
├── notebooks/             # Jupyter notebooks
├── configs/               # YAML configurations
├── data/                  # Datasets (gitignored)
├── docs/                  # Documentation
└── experiments/           # Experiment results
```

## Troubleshooting

### Import Errors

```bash
# Make sure you're in the project root
cd /Users/trungnguyen/Documents/@tum/study/Thesis/agentic-ai-for-clm

# Activate virtual environment
source venv/bin/activate  # or: poetry shell

# Reinstall dependencies
pip install -r requirements.txt
```

### Module Not Found

```bash
# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Test Failures

```bash
# Dependencies might not be installed
pip install -r requirements.txt

# Some tests might need API keys
# Edit .env and add your keys
```

## Getting Help

1. **Documentation:** Check `docs/` directory
2. **Status:** Read `PROJECT_STATUS.md` for current state
3. **Issues:** Common issues documented in `docs/SETUP.md`

## Ready to Code?

Start with these files:

1. `src/agents/risk_agent.py` - Implement risk analysis logic
2. `src/agents/clause_agent.py` - Implement clause alignment
3. `src/core/llm_client.py` - Create LLM integration (to be created)
4. `src/pipeline/document_processor.py` - Build document pipeline (to be created)
