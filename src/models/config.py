"""Model configuration management.

Centralizes model settings for easy switching between providers and models.
Supports cost tracking and capability declarations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class ModelProvider(str, Enum):
    """Supported model providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a specific model.

    Attributes:
        name: Display name for the model.
        model_id: API model identifier.
        provider: Model provider (anthropic, openai).
        max_tokens: Maximum output tokens.
        context_window: Maximum context window size.
        input_cost_per_1k: Cost per 1000 input tokens (USD).
        output_cost_per_1k: Cost per 1000 output tokens (USD).
        supports_json_mode: Whether model supports JSON output mode.
        supports_vision: Whether model supports image inputs.
        temperature: Default temperature setting.
    """
    name: str
    model_id: str
    provider: ModelProvider
    max_tokens: int = 4096
    context_window: int = 200000
    input_cost_per_1k: float = 0.0
    output_cost_per_1k: float = 0.0
    supports_json_mode: bool = True
    supports_vision: bool = False
    temperature: float = 0.0


# Model registry - add new models here
MODEL_REGISTRY: dict[str, ModelConfig] = {
    # Anthropic Models
    "claude-sonnet": ModelConfig(
        name="Claude 3.5 Sonnet",
        model_id="claude-3-5-sonnet-20241022",  # Use older model for Langfuse compatibility
        provider=ModelProvider.ANTHROPIC,
        max_tokens=8192,
        context_window=200000,
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.015,
        supports_json_mode=True,
    ),
    "claude-opus": ModelConfig(
        name="Claude 4 Opus",
        model_id="claude-opus-4-20250514",
        provider=ModelProvider.ANTHROPIC,
        max_tokens=8192,
        context_window=200000,
        input_cost_per_1k=0.015,
        output_cost_per_1k=0.075,
        supports_json_mode=True,
    ),
    "claude-haiku": ModelConfig(
        name="Claude 3.5 Haiku",
        model_id="claude-3-5-haiku-20241022",
        provider=ModelProvider.ANTHROPIC,
        max_tokens=8192,
        context_window=200000,
        input_cost_per_1k=0.0008,
        output_cost_per_1k=0.004,
        supports_json_mode=True,
    ),
    # OpenAI Models (for comparison baselines)
    "gpt-4o": ModelConfig(
        name="GPT-4o",
        model_id="gpt-4o",
        provider=ModelProvider.OPENAI,
        max_tokens=4096,
        context_window=128000,
        input_cost_per_1k=0.005,
        output_cost_per_1k=0.015,
        supports_json_mode=True,
        supports_vision=True,
    ),
    "gpt-4o-mini": ModelConfig(
        name="GPT-4o Mini",
        model_id="gpt-4o-mini",
        provider=ModelProvider.OPENAI,
        max_tokens=4096,
        context_window=128000,
        input_cost_per_1k=0.00015,
        output_cost_per_1k=0.0006,
        supports_json_mode=True,
    ),
}

# Default model for experiments
DEFAULT_MODEL = "claude-sonnet"


def get_model_config(model_key: str) -> ModelConfig:
    """Get configuration for a model by key.

    Args:
        model_key: Model key from registry (e.g., 'claude-sonnet').

    Returns:
        ModelConfig for the specified model.

    Raises:
        ValueError: If model key not found in registry.
    """
    if model_key not in MODEL_REGISTRY:
        available = ", ".join(MODEL_REGISTRY.keys())
        raise ValueError(f"Unknown model: {model_key}. Available: {available}")
    return MODEL_REGISTRY[model_key]


def list_models() -> list[str]:
    """List all available model keys.

    Returns:
        List of model keys.
    """
    return list(MODEL_REGISTRY.keys())


def estimate_cost(
    model_key: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Estimate cost for a model invocation.

    Args:
        model_key: Model key from registry.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.

    Returns:
        Estimated cost in USD.
    """
    config = get_model_config(model_key)
    input_cost = (input_tokens / 1000) * config.input_cost_per_1k
    output_cost = (output_tokens / 1000) * config.output_cost_per_1k
    return input_cost + output_cost
