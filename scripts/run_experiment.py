#!/usr/bin/env python3
"""Single experiment runner for contract clause extraction.

Thin wrapper around run_experiment_pipeline(). For running multiple configs
at once, use scripts/run_batch.py instead.

Usage:
    # Run B1 with a specific model
    uv run python scripts/run_experiment.py --type B1 --model gpt-4.1-mini

    # Run M1 with default samples
    uv run python scripts/run_experiment.py --type M1 --model claude-sonnet-4

    # Quick test run (3 samples per tier)
    uv run python scripts/run_experiment.py --type B1 --model gpt-4.1-mini --samples-per-tier 3

    # Legacy: run from YAML config (backwards compatible)
    uv run python scripts/run_experiment.py --config configs/experiments/baselines.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a single contract extraction experiment",
    )

    # New-style args (preferred)
    parser.add_argument(
        "--type",
        dest="run_type",
        metavar="TYPE",
        help="Run type: B1, B4, M1, M6",
    )
    parser.add_argument(
        "--model",
        dest="model_key",
        metavar="MODEL",
        help="Model key (e.g. gpt-4.1-mini, claude-sonnet-4)",
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
        help="Mark as official run (no test_ prefix)",
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
        help="Override concurrency (default: auto)",
    )

    # Legacy YAML-based args
    parser.add_argument(
        "--config",
        type=str,
        help="(Legacy) Path to experiment config YAML",
    )

    return parser.parse_args()


async def run_from_args(args: argparse.Namespace) -> None:
    """Run experiment from CLI args using the pipeline."""
    from src.experiments.pipeline import ExperimentConfig, run_experiment_pipeline

    cfg = ExperimentConfig(
        model_key=args.model_key,
        run_type=args.run_type,
        samples_per_tier=args.samples_per_tier,
        include_negative=not args.no_negative,
        max_contract_chars=args.max_contract_chars,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        concurrency=args.concurrency,
        is_official=args.official,
    )

    result = await run_experiment_pipeline(
        config=cfg,
        output_dir=Path(args.output_dir),
    )

    print(f"\nDone. Summary: {result.summary_path}")
    print(f"  F1={result.metrics.get('f1', 0):.4f}  "
          f"F2={result.metrics.get('f2', 0):.4f}  "
          f"Jaccard={result.metrics.get('avg_jaccard', 0):.4f}  "
          f"Time={result.elapsed_seconds/60:.1f}m")


async def run_from_yaml(config_path: str, model_override: str | None) -> None:
    """Legacy: run experiments from YAML config file."""
    import yaml

    from src.experiments.pipeline import ExperimentConfig, run_experiment_pipeline

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    # YAML config maps config_name -> {type, model, ...}
    configs = raw.get("configurations", {})
    for config_name, config_data in configs.items():
        model_key = model_override or config_data.get("model", "claude-sonnet-4")
        agent_type = config_data.get("type", "zero_shot")

        # Map YAML type names to run_type codes
        type_map = {
            "zero_shot": "B1",
            "chain_of_thought": "B4",
            "multiagent": "M1",
            "combined_prompts": "M6",
        }
        run_type = type_map.get(agent_type)
        if run_type is None:
            print(f"Skipping unknown type: {agent_type}")
            continue

        cfg = ExperimentConfig(
            model_key=model_key,
            run_type=run_type,
            samples_per_tier=config_data.get("samples_per_tier", 200),
        )

        result = await run_experiment_pipeline(
            config=cfg,
            output_dir=Path(raw.get("output", {}).get("results_dir", "experiments/results")),
        )

        print(f"\n{config_name}: F1={result.metrics.get('f1', 0):.4f}  "
              f"F2={result.metrics.get('f2', 0):.4f}")


async def main() -> None:
    load_dotenv()
    args = parse_args()

    if args.config:
        # Legacy YAML mode
        await run_from_yaml(args.config, args.model_key)
    elif args.run_type and args.model_key:
        # New mode
        await run_from_args(args)
    else:
        print("Error: provide either --type + --model, or --config", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
