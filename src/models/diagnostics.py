"""Model diagnostics and usage tracking.

Tracks token usage, latency, costs across experiments.
Enables model comparison and performance analysis.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
import json
from pathlib import Path


@dataclass
class TokenUsage:
    """Token usage for a single model call."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class ModelCall:
    """Record of a single model invocation."""
    model_key: str
    model_id: str
    timestamp: datetime
    latency_ms: float
    usage: TokenUsage
    cost_usd: float
    success: bool
    error: str | None = None

    # Context
    category: str = ""
    agent_name: str = ""
    experiment_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model_key": self.model_key,
            "model_id": self.model_id,
            "timestamp": self.timestamp.isoformat(),
            "latency_ms": self.latency_ms,
            "usage": self.usage.to_dict(),
            "cost_usd": self.cost_usd,
            "success": self.success,
            "error": self.error,
            "category": self.category,
            "agent_name": self.agent_name,
            "experiment_id": self.experiment_id,
        }


class ModelDiagnostics:
    """Collects and analyzes model usage across an experiment.

    Usage:
        diagnostics = ModelDiagnostics(experiment_id="exp_001")

        # Record calls as they happen
        diagnostics.record_call(model_call)

        # Get summary statistics
        summary = diagnostics.summary()

        # Export for analysis
        diagnostics.export("experiments/diagnostics/exp_001.json")
    """

    def __init__(self, experiment_id: str = "") -> None:
        """Initialize diagnostics collector.

        Args:
            experiment_id: Identifier for this experiment run.
        """
        self.experiment_id = experiment_id
        self.calls: list[ModelCall] = []
        self._start_time = datetime.now()

    def record_call(self, call: ModelCall) -> None:
        """Record a model call.

        Args:
            call: ModelCall record to add.
        """
        if not call.experiment_id:
            call.experiment_id = self.experiment_id
        self.calls.append(call)

    def create_call(
        self,
        model_key: str,
        model_id: str,
        usage: TokenUsage,
        latency_ms: float,
        cost_usd: float,
        success: bool = True,
        error: str | None = None,
        category: str = "",
        agent_name: str = "",
    ) -> ModelCall:
        """Create and record a model call.

        Args:
            model_key: Model registry key.
            model_id: API model identifier.
            usage: Token usage stats.
            latency_ms: Call latency in milliseconds.
            cost_usd: Estimated cost.
            success: Whether call succeeded.
            error: Error message if failed.
            category: CUAD category being processed.
            agent_name: Name of agent making call.

        Returns:
            The created ModelCall record.
        """
        call = ModelCall(
            model_key=model_key,
            model_id=model_id,
            timestamp=datetime.now(),
            latency_ms=latency_ms,
            usage=usage,
            cost_usd=cost_usd,
            success=success,
            error=error,
            category=category,
            agent_name=agent_name,
            experiment_id=self.experiment_id,
        )
        self.record_call(call)
        return call

    def summary(self) -> dict[str, Any]:
        """Generate summary statistics.

        Returns:
            Dictionary with aggregated metrics.
        """
        if not self.calls:
            return {"total_calls": 0}

        successful = [c for c in self.calls if c.success]
        failed = [c for c in self.calls if not c.success]

        total_input = sum(c.usage.input_tokens for c in self.calls)
        total_output = sum(c.usage.output_tokens for c in self.calls)
        total_cost = sum(c.cost_usd for c in self.calls)
        latencies = [c.latency_ms for c in successful]

        # Per-model breakdown
        by_model: dict[str, dict[str, Any]] = {}
        for call in self.calls:
            if call.model_key not in by_model:
                by_model[call.model_key] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                    "avg_latency_ms": 0.0,
                    "latencies": [],
                }
            by_model[call.model_key]["calls"] += 1
            by_model[call.model_key]["input_tokens"] += call.usage.input_tokens
            by_model[call.model_key]["output_tokens"] += call.usage.output_tokens
            by_model[call.model_key]["cost_usd"] += call.cost_usd
            if call.success:
                by_model[call.model_key]["latencies"].append(call.latency_ms)

        # Calculate averages
        for model_stats in by_model.values():
            lats = model_stats.pop("latencies")
            model_stats["avg_latency_ms"] = sum(lats) / len(lats) if lats else 0

        # Per-agent breakdown
        by_agent: dict[str, int] = {}
        for call in self.calls:
            by_agent[call.agent_name] = by_agent.get(call.agent_name, 0) + 1

        return {
            "experiment_id": self.experiment_id,
            "total_calls": len(self.calls),
            "successful_calls": len(successful),
            "failed_calls": len(failed),
            "success_rate": len(successful) / len(self.calls),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": total_cost,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "by_model": by_model,
            "by_agent": by_agent,
            "duration_seconds": (datetime.now() - self._start_time).total_seconds(),
        }

    def export(self, path: str | Path) -> None:
        """Export diagnostics to JSON file.

        Args:
            path: Output file path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "experiment_id": self.experiment_id,
            "start_time": self._start_time.isoformat(),
            "summary": self.summary(),
            "calls": [c.to_dict() for c in self.calls],
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def compare_models(self) -> dict[str, dict[str, float]]:
        """Compare performance across models.

        Returns:
            Comparison metrics per model.
        """
        summary = self.summary()
        by_model = summary.get("by_model", {})

        comparison = {}
        for model_key, stats in by_model.items():
            comparison[model_key] = {
                "calls": stats["calls"],
                "tokens_per_call": (
                    (stats["input_tokens"] + stats["output_tokens"]) / stats["calls"]
                    if stats["calls"] > 0 else 0
                ),
                "cost_per_call": stats["cost_usd"] / stats["calls"] if stats["calls"] > 0 else 0,
                "avg_latency_ms": stats["avg_latency_ms"],
            }

        return comparison
