#!/usr/bin/env python3
"""Main experiment runner for contract clause extraction.

Usage:
    python scripts/run_experiment.py --config configs/experiments/baselines.yaml
    python scripts/run_experiment.py --config configs/experiments/multiagent.yaml --model claude-sonnet-4-20250514
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv
from tqdm import tqdm

from src.data import CUADDataLoader
from src.evaluation import evaluate_batch, EvaluationResult


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load experiment configuration from YAML.

    Args:
        config_path: Path to config file.

    Returns:
        Configuration dictionary.
    """
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_agent_for_config(config_name: str, config: dict):
    """Get the appropriate agent for a configuration.

    Args:
        config_name: Name of the configuration (e.g., 'B1_zero_shot').
        config: Configuration dictionary.

    Returns:
        Configured agent instance.
    """
    agent_type = config.get("type", "zero_shot")

    if agent_type == "zero_shot":
        from src.baselines import ZeroShotBaseline
        return ZeroShotBaseline()
    elif agent_type == "chain_of_thought":
        from src.baselines import ChainOfThoughtBaseline
        return ChainOfThoughtBaseline()
    elif agent_type == "combined_prompts":
        from src.baselines import CombinedPromptsBaseline
        return CombinedPromptsBaseline()
    elif agent_type == "multiagent":
        # TODO: Build multi-agent system
        raise NotImplementedError("Multi-agent system not yet implemented")
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


async def run_single_config(
    config_name: str,
    config: dict,
    data_loader: CUADDataLoader,
    output_dir: Path,
) -> EvaluationResult:
    """Run a single experiment configuration.

    Args:
        config_name: Name of this configuration.
        config: Configuration dictionary.
        data_loader: Loaded CUAD dataset.
        output_dir: Directory for outputs.

    Returns:
        EvaluationResult for this configuration.
    """
    logger.info(f"Running configuration: {config_name}")

    agent = get_agent_for_config(config_name, config)

    predictions: list[str] = []
    ground_truths: list[str] = []
    contract_texts: list[str] = []
    categories: list[str] = []

    samples = list(data_loader)
    for sample in tqdm(samples, desc=config_name):
        try:
            result = await agent.extract(
                contract_text=sample.contract_text,
                category=sample.category,
                question=sample.question,
            )
            # Join extracted clauses for evaluation
            prediction = "\n\n".join(result.extracted_clauses) if result.extracted_clauses else ""
        except NotImplementedError:
            # Agent not yet implemented - skip
            logger.warning(f"Agent {config_name} not implemented, skipping")
            return EvaluationResult()

        predictions.append(prediction)
        ground_truths.append(sample.ground_truth)
        contract_texts.append(sample.contract_text)
        categories.append(sample.category)

    # Evaluate
    eval_result = evaluate_batch(
        predictions=predictions,
        ground_truths=ground_truths,
        contract_texts=contract_texts,
        categories=categories,
    )

    # Save predictions
    predictions_file = output_dir / f"{config_name}_predictions.json"
    with open(predictions_file, "w") as f:
        json.dump(
            {
                "config_name": config_name,
                "timestamp": datetime.now().isoformat(),
                "predictions": [
                    {
                        "sample_id": samples[i].id,
                        "category": categories[i],
                        "prediction": predictions[i],
                        "ground_truth": ground_truths[i],
                    }
                    for i in range(len(predictions))
                ],
            },
            f,
            indent=2,
        )

    logger.info(f"Saved predictions to {predictions_file}")
    return eval_result


async def run_experiment(config_path: str, model: str | None = None) -> dict:
    """Run a full experiment from config file.

    Args:
        config_path: Path to experiment config YAML.
        model: Optional model override.

    Returns:
        Dictionary of results per configuration.
    """
    load_dotenv()

    config = load_config(config_path)
    logger.info(f"Running experiment: {config['experiment_name']}")

    # Load dataset
    data_loader = CUADDataLoader(split="test")
    data_loader.load()
    logger.info(f"Loaded {len(data_loader)} samples")

    # Create output directories
    results_dir = Path(config["output"]["results_dir"])
    results_dir.mkdir(parents=True, exist_ok=True)

    # Run each configuration
    results: dict[str, EvaluationResult] = {}

    for config_name, config_data in config["configurations"].items():
        if model:
            config_data["model"] = model

        result = await run_single_config(
            config_name=config_name,
            config=config_data,
            data_loader=data_loader,
            output_dir=results_dir,
        )
        results[config_name] = result

        # Log summary
        logger.info(
            f"{config_name}: F1={result.f1:.3f}, F2={result.f2:.3f}, "
            f"Jaccard={result.jaccard:.3f}, Laziness={result.laziness_rate:.3f}"
        )

    # Save aggregate results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"results_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(
            {
                "experiment": config["experiment_name"],
                "timestamp": datetime.now().isoformat(),
                "results": {
                    name: {
                        "f1": r.f1,
                        "f2": r.f2,
                        "precision": r.precision,
                        "recall": r.recall,
                        "jaccard": r.jaccard,
                        "laziness_rate": r.laziness_rate,
                        "grounding_rate": r.grounding_rate,
                        "tp": r.tp,
                        "tn": r.tn,
                        "fp": r.fp,
                        "fn": r.fn,
                    }
                    for name, r in results.items()
                },
            },
            f,
            indent=2,
        )

    logger.info(f"Saved results to {results_file}")
    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run contract extraction experiment")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to experiment config YAML",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model override (e.g., claude-sonnet-4-20250514)",
    )
    args = parser.parse_args()

    asyncio.run(run_experiment(args.config, args.model))


if __name__ == "__main__":
    main()
