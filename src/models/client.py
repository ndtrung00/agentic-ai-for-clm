"""Unified model client for multiple providers.

Provides a consistent interface for calling different LLM providers.
Integrates with Langfuse for cost/token tracking.
"""

import os
import time
from typing import Any

from langfuse import get_client as get_langfuse_client

from src.models.config import ModelConfig, ModelProvider, get_model_config
from src.models.diagnostics import ModelDiagnostics, TokenUsage


# Lazy imports to avoid loading unused dependencies
_anthropic_client = None
_openai_client = None
_google_client = None
_ollama_clients: dict[str, Any] = {}


def _get_anthropic_client():
    """Get or create Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        from anthropic import Anthropic
        _anthropic_client = Anthropic()
    return _anthropic_client


def _get_openai_client():
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        _openai_client = OpenAI()
    return _openai_client


def _get_google_client():
    """Get or create Google Gemini client (via OpenAI-compatible API)."""
    global _google_client
    if _google_client is None:
        from openai import OpenAI
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        _google_client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=api_key,
        )
    return _google_client


def _get_ollama_client(base_url: str = "http://localhost:11434/v1"):
    """Get or create Ollama client (OpenAI-compatible).

    Args:
        base_url: Ollama server URL.
    """
    global _ollama_clients
    if base_url not in _ollama_clients:
        from openai import OpenAI
        _ollama_clients[base_url] = OpenAI(base_url=base_url, api_key="ollama")
    return _ollama_clients[base_url]


def get_client(provider: ModelProvider, base_url: str | None = None):
    """Get client for a provider.

    Args:
        provider: Model provider enum.
        base_url: Optional base URL override (used for Ollama).

    Returns:
        Provider client instance.
    """
    if provider == ModelProvider.ANTHROPIC:
        return _get_anthropic_client()
    if provider == ModelProvider.OPENAI:
        return _get_openai_client()
    if provider == ModelProvider.GOOGLE:
        return _get_google_client()
    if provider == ModelProvider.OLLAMA:
        return _get_ollama_client(base_url or "http://localhost:11434/v1")
    raise ValueError(f"Unknown provider: {provider}")


async def invoke_model(
    model_key: str,
    messages: list[dict[str, str]],
    system: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    json_mode: bool = False,
    diagnostics: ModelDiagnostics | None = None,
    agent_name: str = "",
    category: str = "",
) -> tuple[str, TokenUsage]:
    """Invoke a model with unified interface.

    Args:
        model_key: Model key from registry.
        messages: List of message dicts with 'role' and 'content'.
        system: Optional system prompt.
        temperature: Override default temperature.
        max_tokens: Override default max tokens.
        json_mode: Request JSON output format.
        diagnostics: Optional diagnostics collector.
        agent_name: Agent name for tracking.
        category: Category being processed.

    Returns:
        Tuple of (response_text, token_usage).

    Raises:
        ValueError: If model not found.
        Exception: If API call fails.
    """
    config = get_model_config(model_key)
    temp = temperature if temperature is not None else config.temperature
    tokens = max_tokens if max_tokens is not None else config.max_tokens

    start_time = time.perf_counter()

    try:
        if config.provider == ModelProvider.ANTHROPIC:
            response_text, usage = await _invoke_anthropic(
                config=config,
                messages=messages,
                system=system,
                temperature=temp,
                max_tokens=tokens,
            )
        elif config.provider in (ModelProvider.OPENAI, ModelProvider.GOOGLE, ModelProvider.OLLAMA):
            response_text, usage = await _invoke_openai_compatible(
                config=config,
                messages=messages,
                system=system,
                temperature=temp,
                max_tokens=tokens,
                json_mode=json_mode,
            )
        else:
            raise ValueError(f"Unknown provider: {config.provider}")

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Record diagnostics
        if diagnostics is not None:
            from src.models.config import estimate_cost
            cost = estimate_cost(model_key, usage.input_tokens, usage.output_tokens)
            diagnostics.create_call(
                model_key=model_key,
                model_id=config.model_id,
                usage=usage,
                latency_ms=latency_ms,
                cost_usd=cost,
                success=True,
                agent_name=agent_name,
                category=category,
            )

        return response_text, usage

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000

        if diagnostics is not None:
            diagnostics.create_call(
                model_key=model_key,
                model_id=config.model_id,
                usage=TokenUsage(),
                latency_ms=latency_ms,
                cost_usd=0,
                success=False,
                error=str(e),
                agent_name=agent_name,
                category=category,
            )
        raise


async def _invoke_anthropic(
    config: ModelConfig,
    messages: list[dict[str, str]],
    system: str | None,
    temperature: float,
    max_tokens: int,
) -> tuple[str, TokenUsage]:
    """Invoke Anthropic API with Langfuse tracking.

    Args:
        config: Model configuration.
        messages: Message list.
        system: System prompt.
        temperature: Temperature setting.
        max_tokens: Max output tokens.

    Returns:
        Tuple of (response_text, token_usage).
    """
    client = _get_anthropic_client()
    langfuse = get_langfuse_client()

    # Build request
    kwargs: dict[str, Any] = {
        "model": config.model_id,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system:
        kwargs["system"] = system

    # Use context manager for generation tracking
    with langfuse.start_as_current_generation(
        name="anthropic-completion",
        model=config.model_id,
        input=messages,
        metadata={"system": system, "temperature": temperature, "max_tokens": max_tokens},
    ) as generation:
        # Make API call
        response = client.messages.create(**kwargs)

        # Extract response
        response_text = ""
        for block in response.content:
            if hasattr(block, "text"):
                response_text += block.text

        # Extract usage
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cache_read = getattr(response.usage, "cache_read_input_tokens", 0) or 0
        cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0) or 0

        # Calculate costs
        input_cost = (input_tokens / 1000) * config.input_cost_per_1k
        output_cost = (output_tokens / 1000) * config.output_cost_per_1k
        cache_cost = (cache_read / 1000) * config.input_cost_per_1k * 0.1

        # Update generation with output and usage
        generation.update(
            output=response_text,
            usage_details={
                "input": input_tokens,
                "output": output_tokens,
                "cache_read_input_tokens": cache_read,
            },
            cost_details={
                "input": input_cost,
                "output": output_cost,
                "cache_read_input_tokens": cache_cost,
            },
        )

    usage = TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_creation,
    )

    return response_text, usage


async def _invoke_openai_compatible(
    config: ModelConfig,
    messages: list[dict[str, str]],
    system: str | None,
    temperature: float,
    max_tokens: int,
    json_mode: bool = False,
) -> tuple[str, TokenUsage]:
    """Invoke an OpenAI-compatible API (OpenAI, Google Gemini, Ollama) with Langfuse tracking.

    Args:
        config: Model configuration.
        messages: Message list.
        system: System prompt.
        temperature: Temperature setting.
        max_tokens: Max output tokens.
        json_mode: Request JSON output.

    Returns:
        Tuple of (response_text, token_usage).
    """
    if config.provider == ModelProvider.OLLAMA:
        client = _get_ollama_client(config.base_url or "http://localhost:11434/v1")
    elif config.provider == ModelProvider.GOOGLE:
        client = _get_google_client()
    else:
        client = _get_openai_client()

    langfuse = get_langfuse_client()

    # Prepend system message if provided
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    # Build request
    kwargs: dict[str, Any] = {
        "model": config.model_id,
        "messages": full_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    gen_name = f"{config.provider.value}-completion"

    # Use context manager for generation tracking
    with langfuse.start_as_current_generation(
        name=gen_name,
        model=config.model_id,
        input=full_messages,
        metadata={"temperature": temperature, "max_tokens": max_tokens, "json_mode": json_mode},
    ) as generation:
        response = client.chat.completions.create(**kwargs)

        # Extract response
        response_text = response.choices[0].message.content or ""

        # Extract usage
        input_tokens = response.usage.prompt_tokens if response.usage else 0
        output_tokens = response.usage.completion_tokens if response.usage else 0

        # Calculate costs (zero for Ollama/local models)
        input_cost = (input_tokens / 1000) * config.input_cost_per_1k
        output_cost = (output_tokens / 1000) * config.output_cost_per_1k

        # Update generation with output and usage
        generation.update(
            output=response_text,
            usage_details={
                "input": input_tokens,
                "output": output_tokens,
            },
            cost_details={
                "input": input_cost,
                "output": output_cost,
            },
        )

    usage = TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    return response_text, usage
