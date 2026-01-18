#!/usr/bin/env python3
"""Post-hoc analysis of experiment results.

Usage:
    python scripts/analyze_results.py --results experiments/results/
"""

import argparse
import json
from pathlib import Path

import numpy as np

from src.evaluation import (
    mcnemar_test,
    cohens_d,
    format_result,
)
from src.data import CATEGORY_TIERS


def load_results(results_dir: Path) -> dict:
    """Load all result files from directory.

    Args:
        results_dir: Path to results directory.

    Returns:
        Dictionary mapping experiment names to results.
    """
    results = {}
    for file in results_dir.glob("results_*.json"):
        with open(file) as f:
            data = json.load(f)
            results[file.stem] = data
    return results


def load_predictions(results_dir: Path) -> dict:
    """Load all prediction files from directory.

    Args:
        results_dir: Path to results directory.

    Returns:
        Dictionary mapping config names to predictions.
    """
    predictions = {}
    for file in results_dir.glob("*_predictions.json"):
        with open(file) as f:
            data = json.load(f)
            config_name = data["config_name"]
            predictions[config_name] = data["predictions"]
    return predictions


def analyze_by_tier(predictions: dict, config_a: str, config_b: str) -> dict:
    """Compare two configurations by category tier.

    Args:
        predictions: Dictionary of predictions by config.
        config_a: First configuration name.
        config_b: Second configuration name.

    Returns:
        Dictionary of tier-wise comparison results.
    """
    results = {}

    preds_a = predictions.get(config_a, [])
    preds_b = predictions.get(config_b, [])

    if not preds_a or not preds_b:
        return results

    for tier in ["common", "moderate", "rare"]:
        tier_categories = CATEGORY_TIERS.get(tier, [])

        # Filter predictions by tier
        tier_preds_a = [p for p in preds_a if p["category"] in tier_categories]
        tier_preds_b = [p for p in preds_b if p["category"] in tier_categories]

        if not tier_preds_a:
            continue

        # Simple accuracy comparison
        correct_a = [
            1 if p["prediction"].strip() and p["ground_truth"].strip() and
            p["ground_truth"] in p["prediction"] else 0
            for p in tier_preds_a
        ]
        correct_b = [
            1 if p["prediction"].strip() and p["ground_truth"].strip() and
            p["ground_truth"] in p["prediction"] else 0
            for p in tier_preds_b
        ]

        results[tier] = {
            "n_samples": len(tier_preds_a),
            "accuracy_a": np.mean(correct_a) if correct_a else 0,
            "accuracy_b": np.mean(correct_b) if correct_b else 0,
            "improvement": np.mean(correct_b) - np.mean(correct_a) if correct_a else 0,
        }

    return results


def compare_configs(
    results: dict,
    predictions: dict,
    config_a: str,
    config_b: str,
) -> dict:
    """Statistical comparison of two configurations.

    Args:
        results: Aggregate results dictionary.
        predictions: Predictions dictionary.
        config_a: First configuration (baseline).
        config_b: Second configuration (treatment).

    Returns:
        Comparison results with statistical tests.
    """
    # Find results for each config
    result_a = None
    result_b = None

    for exp_results in results.values():
        if "results" in exp_results:
            if config_a in exp_results["results"]:
                result_a = exp_results["results"][config_a]
            if config_b in exp_results["results"]:
                result_b = exp_results["results"][config_b]

    if not result_a or not result_b:
        return {"error": "Could not find results for both configurations"}

    comparison = {
        "config_a": config_a,
        "config_b": config_b,
        "f2_a": result_a["f2"],
        "f2_b": result_b["f2"],
        "f2_diff": result_b["f2"] - result_a["f2"],
    }

    # Load predictions for statistical tests
    preds_a = predictions.get(config_a, [])
    preds_b = predictions.get(config_b, [])

    if preds_a and preds_b:
        # Extract correctness for McNemar test
        correct_a = [
            p["prediction"].strip() != "" and p["ground_truth"] in p["prediction"]
            for p in preds_a
        ]
        correct_b = [
            p["prediction"].strip() != "" and p["ground_truth"] in p["prediction"]
            for p in preds_b
        ]

        chi2, p_value = mcnemar_test(correct_a, correct_b)
        comparison["mcnemar_chi2"] = chi2
        comparison["mcnemar_p"] = p_value
        comparison["significant"] = p_value < 0.05

        # Effect size
        scores_a = [1.0 if c else 0.0 for c in correct_a]
        scores_b = [1.0 if c else 0.0 for c in correct_b]
        comparison["cohens_d"] = cohens_d(scores_a, scores_b)

        # Tier analysis
        comparison["by_tier"] = analyze_by_tier(predictions, config_a, config_b)

    return comparison


def generate_report(results: dict, predictions: dict) -> str:
    """Generate analysis report.

    Args:
        results: Aggregate results dictionary.
        predictions: Predictions dictionary.

    Returns:
        Formatted report string.
    """
    lines = [
        "=" * 60,
        "EXPERIMENT RESULTS ANALYSIS",
        "=" * 60,
        "",
    ]

    # Summary of all experiments
    lines.append("## Results Summary")
    lines.append("")

    for exp_name, exp_results in results.items():
        lines.append(f"### {exp_name}")
        lines.append(f"Timestamp: {exp_results.get('timestamp', 'N/A')}")
        lines.append("")

        if "results" in exp_results:
            for config_name, metrics in exp_results["results"].items():
                lines.append(f"**{config_name}**")
                lines.append(f"  F1: {metrics['f1']:.3f}")
                lines.append(f"  F2: {metrics['f2']:.3f}")
                lines.append(f"  Precision: {metrics['precision']:.3f}")
                lines.append(f"  Recall: {metrics['recall']:.3f}")
                lines.append(f"  Jaccard: {metrics['jaccard']:.3f}")
                lines.append(f"  Laziness Rate: {metrics['laziness_rate']:.3f}")
                lines.append("")

    # Key comparisons
    lines.append("")
    lines.append("## Key Comparisons")
    lines.append("")

    # B1 vs M1 (if available)
    comparison = compare_configs(results, predictions, "B1_zero_shot", "M1_full_system")
    if "error" not in comparison:
        lines.append("### B1 (Zero-Shot) vs M1 (Multi-Agent)")
        lines.append(format_result(
            "F2",
            comparison["f2_b"],
            baseline_value=comparison["f2_a"],
            p_value=comparison.get("mcnemar_p"),
            effect_size=comparison.get("cohens_d"),
        ))
        lines.append("")

    # M1 vs M6 (critical ablation)
    comparison = compare_configs(results, predictions, "M6_combined_prompts", "M1_full_system")
    if "error" not in comparison:
        lines.append("### M6 (Combined Prompts) vs M1 (Multi-Agent)")
        lines.append("**Critical ablation: Architecture vs Prompting**")
        lines.append(format_result(
            "F2",
            comparison["f2_b"],
            baseline_value=comparison["f2_a"],
            p_value=comparison.get("mcnemar_p"),
            effect_size=comparison.get("cohens_d"),
        ))
        if comparison.get("significant"):
            lines.append("→ Multi-agent architecture provides genuine benefit")
        else:
            lines.append("→ Benefits may come from prompting, not architecture")
        lines.append("")

    return "\n".join(lines)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analyze experiment results")
    parser.add_argument(
        "--results",
        type=str,
        required=True,
        help="Path to results directory",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for report (optional)",
    )
    args = parser.parse_args()

    results_dir = Path(args.results)
    results = load_results(results_dir)
    predictions = load_predictions(results_dir)

    report = generate_report(results, predictions)
    print(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\nReport saved to {args.output}")


if __name__ == "__main__":
    main()
