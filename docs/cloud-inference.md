# Cloud Inference for Open-Source Models

## Overview

Open-source models in this project (DeepSeek, LLaMA, Gemma, Qwen3) currently run via **Ollama on local GPU**. This works for development but has limitations:

- **No local GPU?** Can't run experiments at all
- **Batch runs** are slow on consumer hardware
- **Reproducibility** depends on specific hardware/quantization

Cloud inference providers offer **OpenAI-compatible APIs** for open-source models, enabling:

- Pay-per-token pricing (no GPU required)
- Parallel batch experiments
- Consistent serving infrastructure across runs

---

## Provider Comparison

We evaluated 5 cloud inference providers against our **8 target open-source models**.

### Target Models

| # | Model                        | Ollama model_id                |
|---|------------------------------|--------------------------------|
| 1 | DeepSeek R1 Distill Qwen 7B  | `deepseek-r1:7b`              |
| 2 | DeepSeek R1 0528 Qwen3 8B    | `deepseek-r1:0528-qwen3-8b`  |
| 3 | LLaMA 3.1 8B Instruct        | `llama3.1:8b`                 |
| 4 | Gemma 3 4B                   | `gemma3:4b`                   |
| 5 | Gemma 3 12B                  | `gemma3:12b`                  |
| 6 | Qwen3 4B                    | `qwen3:4b`                    |
| 7 | Qwen3 8B                    | `qwen3:8b`                    |
| 8 | Qwen3 14B                   | `qwen3:14b`                   |

### Coverage & Pricing

| Provider       | Coverage | LLaMA 3.1 8B (in/out $/1M) | API Compatibility | Pros                                        | Cons                                                    |
|----------------|----------|----------------------------|-------------------|---------------------------------------------|---------------------------------------------------------|
| **OpenRouter** | **8/8**  | $0.02 / $0.05             | OpenAI-compatible | All 8 models; single API key; free tiers    | Pricing volatile; free-tier rate limits (~8 RPM)        |
| **DeepInfra**  | ~2-3/8   | $0.03 / $0.05             | OpenAI-compatible | Cheapest per-token; bare-metal infra        | Smaller Qwen3 models (4B/8B/14B) not on serverless tier |
| **Fireworks**  | ~5-6/8   | $0.20 / $0.20             | OpenAI-compatible | Good quantized model support (AWQ/FP8)      | Gemma 3 and DeepSeek R1 Distill not confirmed           |
| **Groq**       | 1/8      | $0.05 / $0.08             | OpenAI-compatible | Extremely fast (~397 tok/sec)               | Very limited catalog; no Qwen3/Gemma/DeepSeek small     |
| **Together**   | 1/8      | $0.18 / $0.18             | OpenAI-compatible | 200+ models                                 | Qwen3 4B/8B require dedicated endpoints; not serverless |

### Detailed Coverage Matrix

| Model                        | OpenRouter       | DeepInfra      | Fireworks      | Groq | Together          |
|------------------------------|------------------|----------------|----------------|------|-------------------|
| DeepSeek R1 Distill Qwen 7B | Yes (free)       | Not confirmed  | Not confirmed  | No   | No                |
| DeepSeek R1 0528 Qwen3 8B   | Yes (free)       | Not confirmed  | Not confirmed  | No   | No                |
| LLaMA 3.1 8B Instruct       | Yes              | Yes            | Yes            | Yes  | Yes               |
| Gemma 3 4B                   | Yes              | Yes            | Likely         | No   | No                |
| Gemma 3 12B                  | Yes              | Not confirmed  | Likely         | No   | No                |
| Qwen3 4B                    | Yes (free)       | Not confirmed  | Likely         | No   | Dedicated only    |
| Qwen3 8B                    | Yes              | Not confirmed  | Likely         | No   | Dedicated only    |
| Qwen3 14B                   | Yes              | Not confirmed  | Likely         | No   | Not confirmed     |

---

## Recommendation

### Primary: OpenRouter

**OpenRouter is the recommended provider** because it has **100% coverage** of all 8 target models through a single API key. It aggregates multiple backend providers and automatically routes to the cheapest available option.

### Future: DeepInfra

DeepInfra offers the **cheapest per-token pricing** (often 50-80% less than competitors) and is planned as a future addition once smaller Qwen3 models appear on their serverless tier.

---

## OpenRouter Model Mapping

Registry keys use the **`-or` suffix** appended to the base Ollama key.

| Registry Key                     | OpenRouter `model_id`                         | Input ($/1M) | Output ($/1M) |
|----------------------------------|-----------------------------------------------|-------------|---------------|
| `deepseek-r1-distill-qwen-7b-or`| `deepseek/deepseek-r1-distill-qwen-7b`        | Free*       | Free*         |
| `deepseek-r1-0528-qwen3-8b-or`  | `deepseek/deepseek-r1-0528-qwen3-8b`          | Free*       | Free*         |
| `llama-3.1-8b-or`               | `meta-llama/llama-3.1-8b-instruct`             | $0.02       | $0.05         |
| `gemma-3-4b-or`                 | `google/gemma-3-4b-it`                         | $0.04       | $0.08         |
| `gemma-3-12b-or`                | `google/gemma-3-12b-it`                        | $0.04       | $0.13         |
| `qwen3-4b-or`                   | `qwen/qwen3-4b`                               | Free*       | Free*         |
| `qwen3-4b-thinking-or`          | `qwen/qwen3-4b`                               | Free*       | Free*         |
| `qwen3-8b-or`                   | `qwen/qwen3-8b`                               | $0.05       | $0.40         |
| `qwen3-8b-thinking-or`          | `qwen/qwen3-8b`                               | $0.05       | $0.40         |
| `qwen3-14b-or`                  | `qwen/qwen3-14b`                              | $0.06       | $0.24         |
| `qwen3-14b-thinking-or`         | `qwen/qwen3-14b`                              | $0.06       | $0.24         |

**13 total entries** (8 base + 3 thinking variants for Qwen3 4B/8B/14B). AWQ/FP8 variants are not needed since OpenRouter abstracts quantization.

\* Free-tier models have strict rate limits (~8 RPM). The existing `tenacity` retry with exponential backoff handles 429s, but experiment throughput will be slower.

---

## Setup

### 1. Get an API key

Sign up at [openrouter.ai](https://openrouter.ai/) and create an API key.

### 2. Add to `.env`

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

### 3. Verify

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="sk-or-v1-...",
    default_headers={
        "HTTP-Referer": "https://github.com/ndtrung00/agentic-ai-for-clm",
        "X-Title": "CLM Multi-Agent Thesis",
    },
)

response = client.chat.completions.create(
    model="qwen/qwen3-4b",
    messages=[{"role": "user", "content": "Hello"}],
    max_tokens=50,
)
print(response.choices[0].message.content)
```

---

## Usage

Switch to an OpenRouter model in notebooks by changing `MODEL_KEY`:

```python
# Before (local Ollama):
MODEL_KEY = "qwen3-8b"

# After (cloud via OpenRouter):
MODEL_KEY = "qwen3-8b-or"
```

Everything else (experiment runner, evaluation, diagnostics) works identically -- the provider is determined by the registry entry.

---

## Caveats

1. **Free-tier rate limits**: Models marked "Free" have ~8 RPM limits. Batch experiments will be throttled. Consider using paid models or adding credits for production runs.

2. **Pricing volatility**: OpenRouter aggregates providers dynamically. Prices may change as backend providers join/leave. The costs in the model mapping table are snapshots. A future enhancement could fetch live pricing from `https://openrouter.ai/api/v1/models` at experiment start.

3. **Required headers**: OpenRouter requires `HTTP-Referer` and `X-Title` headers for identification and to access free models.

4. **No AWQ/FP8 control**: OpenRouter abstracts quantization choices. If you need specific quantization (e.g., for reproducibility against Ollama AWQ runs), use Ollama locally instead.

5. **Context window**: OpenRouter model context windows may differ from Ollama defaults. Verify via the OpenRouter model page if running very long contracts.

---

## Future: DeepInfra

Planned as a second cloud provider with `-di` suffix convention:

| Convention | Example |
|-----------|---------|
| Base      | `qwen3-8b-di` |
| Thinking  | `qwen3-8b-thinking-di` |

**Why not now?** Smaller Qwen3 models (4B, 8B, 14B) are not yet available on DeepInfra's serverless tier. Only larger models (32B+) are listed.

**Known DeepInfra pricing** (for reference):

| Model                | Input ($/1M) | Output ($/1M) |
|----------------------|-------------|---------------|
| LLaMA 3.1 8B        | $0.03       | $0.05         |
| Gemma 3 4B           | $0.04       | $0.08         |
| Qwen3 32B            | $0.08       | $0.28         |

When DeepInfra adds smaller Qwen3 models to serverless, a `DEEPINFRA` provider can be added to `ModelProvider` enum and `MODEL_REGISTRY` following the same pattern as OpenRouter.
