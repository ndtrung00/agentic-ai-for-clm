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
    GOOGLE = "google"
    OLLAMA = "ollama"


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a specific model.

    Attributes:
        name: Display name for the model.
        model_id: API model identifier.
        provider: Model provider (anthropic, openai, google, ollama).
        max_tokens: Maximum output tokens.
        context_window: Maximum context window size.
        input_cost_per_1k: Cost per 1000 input tokens (USD).
        output_cost_per_1k: Cost per 1000 output tokens (USD).
        supports_json_mode: Whether model supports JSON output mode.
        supports_vision: Whether model supports image inputs.
        temperature: Default temperature setting.
        base_url: Optional base URL override (for Ollama or custom endpoints).
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
    base_url: str | None = None


# ---------------------------------------------------------------------------
# Model registry — ContractEval paper models (19 LLMs)
# Proprietary: 4 | Open-source via Ollama: 15
#
# Qwen3 "thinking" variants use the SAME model_id; the difference is
# controlled at the prompt level (/think vs /no_think system tag).
# AWQ/FP8 quantisation variants may require vLLM serving instead of Ollama;
# adjust base_url accordingly.
# ---------------------------------------------------------------------------

MODEL_REGISTRY: dict[str, ModelConfig] = {
    # ── Proprietary models ────────────────────────────────────────────────

    # Anthropic
    "claude-sonnet-4": ModelConfig(
        name="Claude Sonnet 4",
        model_id="claude-sonnet-4-20250514",
        provider=ModelProvider.ANTHROPIC,
        max_tokens=8192,
        context_window=200000,
        input_cost_per_1k=0.003,
        output_cost_per_1k=0.015,
    ),

    # OpenAI
    "gpt-4.1": ModelConfig(
        name="GPT 4.1",
        model_id="gpt-4.1",
        provider=ModelProvider.OPENAI,
        max_tokens=32768,
        context_window=1047576,
        input_cost_per_1k=0.002,
        output_cost_per_1k=0.008,
    ),
    "gpt-4.1-mini": ModelConfig(
        name="GPT 4.1 Mini",
        model_id="gpt-4.1-mini",
        provider=ModelProvider.OPENAI,
        max_tokens=32768,
        context_window=1047576,
        input_cost_per_1k=0.0004,
        output_cost_per_1k=0.0016,
    ),

    # Google
    "gemini-2.5-pro": ModelConfig(
        name="Gemini 2.5 Pro Preview",
        model_id="gemini-2.5-pro-preview-05-06",
        provider=ModelProvider.GOOGLE,
        max_tokens=8192,
        context_window=1048576,
        input_cost_per_1k=0.00125,
        output_cost_per_1k=0.01,
    ),

    # ── Open-source models (Ollama) ──────────────────────────────────────

    # DeepSeek
    "deepseek-r1-distill-qwen-7b": ModelConfig(
        name="DeepSeek R1 Distill Qwen 7B",
        model_id="deepseek-r1:7b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),
    "deepseek-r1-0528-qwen3-8b": ModelConfig(
        name="DeepSeek R1 0528 Qwen3 8B",
        model_id="deepseek-r1:0528-qwen3-8b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),

    # LLaMA
    "llama-3.1-8b": ModelConfig(
        name="LLaMA 3.1 8B Instruct",
        model_id="llama3.1:8b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),

    # Gemma
    "gemma-3-4b": ModelConfig(
        name="Gemma 3 4B",
        model_id="gemma3:4b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),
    "gemma-3-12b": ModelConfig(
        name="Gemma 3 12B",
        model_id="gemma3:12b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),

    # Qwen3 4B
    "qwen3-4b": ModelConfig(
        name="Qwen3 4B",
        model_id="qwen3:4b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),
    "qwen3-4b-thinking": ModelConfig(
        name="Qwen3 4B (thinking)",
        model_id="qwen3:4b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),

    # Qwen3 8B
    "qwen3-8b": ModelConfig(
        name="Qwen3 8B",
        model_id="qwen3:8b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),
    "qwen3-8b-thinking": ModelConfig(
        name="Qwen3 8B (thinking)",
        model_id="qwen3:8b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),

    # Qwen3 8B AWQ (may require vLLM serving)
    "qwen3-8b-awq": ModelConfig(
        name="Qwen3 8B AWQ",
        model_id="qwen3:8b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),
    "qwen3-8b-awq-thinking": ModelConfig(
        name="Qwen3 8B AWQ (thinking)",
        model_id="qwen3:8b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),

    # Qwen3 8B FP8 (may require vLLM serving)
    "qwen3-8b-fp8": ModelConfig(
        name="Qwen3 8B FP8",
        model_id="qwen3:8b-fp8",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),
    "qwen3-8b-fp8-thinking": ModelConfig(
        name="Qwen3 8B FP8 (thinking)",
        model_id="qwen3:8b-fp8",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),

    # Qwen3 14B
    "qwen3-14b": ModelConfig(
        name="Qwen3 14B",
        model_id="qwen3:14b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),
    "qwen3-14b-thinking": ModelConfig(
        name="Qwen3 14B (thinking)",
        model_id="qwen3:14b",
        provider=ModelProvider.OLLAMA,
        max_tokens=4096,
        context_window=128000,
        base_url="http://localhost:11434/v1",
    ),
}

# Default model for experiments
DEFAULT_MODEL = "claude-sonnet-4"


def get_model_config(model_key: str) -> ModelConfig:
    """Get configuration for a model by key.

    Args:
        model_key: Model key from registry (e.g., 'claude-sonnet-4').

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
