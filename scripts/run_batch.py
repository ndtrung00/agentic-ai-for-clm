#!/usr/bin/env python3
"""Batch experiment runner for contract clause extraction.

Runs multiple experiment configs sequentially, sharing CUAD data across runs.
Produces the same output format (summary JSON, intermediate JSONL, diagnostics
JSON) as the interactive notebooks.

Usage:
    # B1 across 3 models
    uv run python scripts/run_batch.py \\
        --type B1 \\
        --models gpt-4.1-mini gpt-4.1 claude-sonnet-4 \\
        --samples-per-tier 200 \\
        --official

    # B1 + B4 for one model
    uv run python scripts/run_batch.py \\
        --type B1 B4 \\
        --models gpt-4.1-mini \\
        --samples-per-tier 200

    # M1 + M6 for one model
    uv run python scripts/run_batch.py \\
        --type M1 M6 \\
        --models claude-sonnet-4 \\
        --samples-per-tier 200

    # Quick smoke test (3 samples per tier)
    uv run python scripts/run_batch.py \\
        --type B1 \\
        --models gpt-4.1-mini \\
        --samples-per-tier 3
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run multiple experiment configs sequentially",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s --type B1 --models gpt-4.1-mini gpt-4.1\n"
            "  %(prog)s --type B1 B4 --models gpt-4.1-mini --official\n"
            "  %(prog)s --type M1 M6 --models claude-sonnet-4\n"
        ),
    )
    parser.add_argument(
        "--type",
        nargs="+",
        required=True,
        dest="run_types",
        metavar="TYPE",
        help="Run types: B1 B4 M1 M6",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        metavar="MODEL",
        help="Model keys (e.g. gpt-4.1-mini claude-sonnet-4)",
    )
    parser.add_argument(
        "--samples-per-tier",
        type=int,
        default=200,
        help="Samples per tier (default: 200)",
    )
    parser.add_argument(
        "--max-contract-chars",
        type=int,
        default=100_000,
        help="Skip contracts longer than this (default: 100000)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Generation temperature (default: 0.0)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Max output tokens (default: 4096)",
    )
    parser.add_argument(
        "--no-negative",
        action="store_true",
        help="Exclude negative (no-clause) samples",
    )
    parser.add_argument(
        "--official",
        action="store_true",
        help="Mark runs as official (no test_ prefix)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/results",
        help="Output directory (default: experiments/results)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=None,
        help="Override concurrency (default: auto, 5 for baselines, 1 for M1)",
    )
    return parser.parse_args()


async def main() -> None:
    load_dotenv()
    args = parse_args()

    from src.experiments.pipeline import ExperimentConfig, run_batch

    # Build config matrix
    configs: list[ExperimentConfig] = []
    for run_type in args.run_types:
        for model_key in args.models:
            configs.append(
                ExperimentConfig(
                    model_key=model_key,
                    run_type=run_type,
                    samples_per_tier=args.samples_per_tier,
                    include_negative=not args.no_negative,
                    max_contract_chars=args.max_contract_chars,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    concurrency=args.concurrency,
                    is_official=args.official,
                )
            )

    completed = await run_batch(
        configs,
        output_dir=Path(args.output_dir),
    )

    if len(completed) < len(configs):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
