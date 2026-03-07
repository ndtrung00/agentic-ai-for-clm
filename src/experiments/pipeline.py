"""Reusable experiment pipeline.

Encapsulates one complete experiment run (data loading, extraction, evaluation,
saving) into a single async function. Used by scripts/run_batch.py for headless
multi-run execution, and by scripts/run_experiment.py as a thin wrapper.

Notebooks remain the interactive single-run tool and are NOT modified.

Notebook usage (sequential)::

    from src.experiments.pipeline import ExperimentConfig, run_batch

    results = await run_batch([
        ExperimentConfig(model_key="gpt-4.1-mini", run_type="B1", samples_per_tier=5),
        ExperimentConfig(model_key="gpt-4.1-mini", run_type="B4", samples_per_tier=5),
        ExperimentConfig(model_key="gpt-4.1",      run_type="B1", samples_per_tier=5),
    ])

Parallel execution (different providers only — same provider shares rate limits)::

    import asyncio
    from src.experiments.pipeline import (
        ExperimentConfig, run_experiment_pipeline, load_and_select_samples,
    )

    samples = load_and_select_samples(samples_per_tier=200, include_negative=True, max_contract_chars=100_000)

    # Safe to parallelize: different providers won't compete for rate limits
    openai_task  = run_experiment_pipeline(ExperimentConfig(model_key="gpt-4.1-mini", run_type="B1"), samples=samples)
    claude_task  = run_experiment_pipeline(ExperimentConfig(model_key="claude-sonnet-4", run_type="B1"), samples=samples)
    gemini_task  = run_experiment_pipeline(ExperimentConfig(model_key="gemini-2.5-flash", run_type="B1"), samples=samples)
    results = await asyncio.gather(openai_task, claude_task, gemini_task)

    # DON'T parallelize: same provider will hit rate limits
    # Bad:  await asyncio.gather(B1_gpt4, B4_gpt4)   # both hammer OpenAI
    # Good: run them sequentially via run_batch(), or use run_batch(parallel=True)
    #       only when configs target different providers.
"""

from __future__ import annotations

import datetime
import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.agents.base import AgentConfig, ExtractionResult
from src.agents.orchestrator import CATEGORY_ROUTING
from src.baselines.chain_of_thought import (
    COT_SYSTEM_PROMPT,
    COT_USER_TEMPLATE,
    ChainOfThoughtBaseline,
)
from src.baselines.combined_prompts import (
    M6_SYSTEM_PROMPT,
    M6_USER_TEMPLATE,
    CombinedPromptsBaseline,
    _get_domain,
    _get_indicators,
    _DOMAIN_EXPERTISE,
)
from src.baselines.zero_shot import CONTRACTEVAL_PROMPT, ZeroShotBaseline
from src.data.cuad_loader import CUADDataLoader, CUADSample
from src.experiments.results import (
    compute_aggregate_metrics,
    compute_per_tier_metrics,
    print_diagnostics,
    print_metrics,
    save_experiment,
)
from src.experiments.runner import ExtractionOutput, run_extraction
from src.models import invoke_model as model_invoke
from src.models.config import get_model_config
from src.models.diagnostics import ModelDiagnostics

# ── Label mappings (mirrors notebooks) ──────────────────────────────────────

RUN_TYPE_LABELS: dict[str, str] = {
    "B1": "zero_shot",
    "B4": "cot",
    "M1": "multiagent",
    "M2": "ablation_no_validation",
    "M3": "ablation_single_specialist",
    "M4": "ablation_no_routing",
    "M5": "ablation_no_specialist_prompts",
    "M6": "combined_prompts",
}

BASELINE_TYPES = {"B1", "B4"}
EXPERIMENT_TYPES = {"M1", "M6"}

_PROMPT_TEMPLATES: dict[str, str] = {
    "B1": CONTRACTEVAL_PROMPT,
    "B4": COT_SYSTEM_PROMPT,
}


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment run."""

    model_key: str
    run_type: str  # "B1", "B4", "M1", "M6"
    samples_per_tier: int = 200
    include_negative: bool = True
    max_contract_chars: int = 100_000
    temperature: float = 0.0
    max_tokens: int = 4096
    concurrency: int | None = None  # None = auto (5 for baselines, 1 for M1)
    is_official: bool = False

    def __post_init__(self) -> None:
        if self.run_type not in RUN_TYPE_LABELS:
            raise ValueError(
                f"Unknown run_type: {self.run_type!r}. "
                f"Must be one of: {sorted(RUN_TYPE_LABELS)}"
            )
        if self.run_type in {"M2", "M3", "M4", "M5"}:
            raise NotImplementedError(
                f"{self.run_type} ablation is not yet implemented. "
                f"Currently available: B1, B4, M1, M6."
            )

    @property
    def run_label(self) -> str:
        return RUN_TYPE_LABELS[self.run_type]

    @property
    def run_type_key(self) -> str:
        return "baseline" if self.run_type in BASELINE_TYPES else "experiment"

    @property
    def effective_concurrency(self) -> int:
        if self.concurrency is not None:
            return self.concurrency
        return 3 if self.run_type == "M1" else 5


@dataclass
class ExperimentResult:
    """Result of a completed experiment run."""

    run_id: str
    config: ExperimentConfig
    summary_path: Path
    diagnostics_path: Path
    intermediate_path: Path
    metrics: dict[str, Any]
    per_tier: dict[str, dict[str, Any]]
    n_samples: int = 0
    n_failures: int = 0
    elapsed_seconds: float = 0.0


# ── Sample loading ──────────────────────────────────────────────────────────


def load_and_select_samples(
    *,
    samples_per_tier: int,
    include_negative: bool,
    max_contract_chars: int,
    seed: int = 42,
) -> list[CUADSample]:
    """Load CUAD data and perform stratified sampling.

    Uses the same logic as notebooks 03/04 for reproducibility.
    """
    random.seed(seed)
    loader = CUADDataLoader()
    loader.load()
    all_samples = list(loader)

    by_tier: dict[str, list[CUADSample]] = defaultdict(list)
    for s in all_samples:
        if len(s.contract_text) <= max_contract_chars:
            by_tier[s.tier].append(s)

    selected: list[CUADSample] = []
    for tier in ["common", "moderate", "rare"]:
        tier_samples = by_tier[tier]
        positive = [s for s in tier_samples if s.has_clause]
        negative = [s for s in tier_samples if not s.has_clause]

        n_pos = min(samples_per_tier, len(positive))
        selected.extend(random.sample(positive, n_pos))

        if include_negative and negative:
            n_neg = min(max(1, samples_per_tier // 2), len(negative))
            selected.extend(random.sample(negative, n_neg))

    return selected


# ── Extract function builders ───────────────────────────────────────────────


def _build_baseline_messages(
    sample: CUADSample, run_type: str
) -> tuple[str, str]:
    """Build (system_prompt, user_message) for B1/B4."""
    if run_type == "B1":
        system_prompt = CONTRACTEVAL_PROMPT
        user_msg = (
            f"Context:\n{sample.contract_text}\n\n"
            f"Question:\n{sample.question}"
        )
        return system_prompt, user_msg
    elif run_type == "B4":
        system_prompt = COT_SYSTEM_PROMPT
        user_msg = COT_USER_TEMPLATE.format(
            contract_text=sample.contract_text,
            question=sample.question,
        )
        return system_prompt, user_msg
    else:
        raise ValueError(f"Not a baseline type: {run_type}")


_PARSERS: dict[str, ZeroShotBaseline | ChainOfThoughtBaseline] = {
    "B1": ZeroShotBaseline(),
    "B4": ChainOfThoughtBaseline(),
}


def _parse_baseline_response(
    raw_response: str, category: str, run_type: str
) -> ExtractionResult:
    """Parse raw model response using baseline-specific parser."""
    parser = _PARSERS[run_type]
    result = parser.parse_response(raw_response)
    result.category = category
    return result


# ── Main pipeline ───────────────────────────────────────────────────────────


async def run_experiment_pipeline(
    config: ExperimentConfig,
    samples: list[CUADSample] | None = None,
    output_dir: Path | str = Path("experiments/results"),
) -> ExperimentResult:
    """Run one complete experiment: extraction + evaluation + save.

    Args:
        config: Experiment configuration.
        samples: Pre-loaded samples (shared across batch runs). If None,
            loads and samples fresh via ``load_and_select_samples``.
        output_dir: Directory for result files.

    Returns:
        ExperimentResult with paths to saved files and computed metrics.
    """
    import time

    t_start = time.monotonic()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Load samples if not provided ──
    if samples is None:
        samples = load_and_select_samples(
            samples_per_tier=config.samples_per_tier,
            include_negative=config.include_negative,
            max_contract_chars=config.max_contract_chars,
        )

    # ── 2. Resolve model config ──
    model_cfg = get_model_config(config.model_key)

    # ── 3. Generate run ID ──
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_prefix = "" if config.is_official else "test_"
    run_id = f"{run_prefix}{config.run_label}_{config.model_key}_{timestamp}"

    intermediate_path = output_dir / f"{run_id}_intermediate.jsonl"

    # ── 4. Set up diagnostics and extract_fn ──
    diagnostics: ModelDiagnostics
    extract_fn: Any  # async callable

    if config.run_type in BASELINE_TYPES:
        diagnostics = ModelDiagnostics(experiment_id=run_id)
        extract_fn = _make_baseline_extract_fn(config, diagnostics)

    elif config.run_type == "M1":
        diagnostics, extract_fn, orchestrator, specialists = (
            _make_m1_extract_fn(config, run_id=run_id)
        )

    elif config.run_type == "M6":
        diagnostics, extract_fn, m6_baseline = _make_m6_extract_fn(config, run_id=run_id)

    else:
        raise NotImplementedError(f"{config.run_type} is not implemented")

    # ── 5. Run extraction ──
    print(f"\n{'='*60}")
    print(f"  {config.run_type} | {config.model_key} | {len(samples)} samples")
    print(f"  run_id: {run_id}")
    print(f"{'='*60}\n")

    results, failures = await run_extraction(
        samples,
        extract_fn,
        run_id=run_id,
        model_key=config.model_key,
        model_id=model_cfg.model_id,
        run_type=config.run_type,
        run_label=config.run_label,
        run_type_key=config.run_type_key,
        intermediate_path=intermediate_path,
        concurrency=config.effective_concurrency,
        is_official=config.is_official,
    )

    # ── 6. Compute metrics ──
    metrics = compute_aggregate_metrics(results)
    per_tier = compute_per_tier_metrics(results)
    print_metrics(
        metrics,
        per_tier,
        run_type=config.run_type,
        run_label=config.run_label,
        model_key=config.model_key,
    )

    diag_summary = print_diagnostics(diagnostics, config.model_key)

    # ── 7. Build prompt/architecture info ──
    prompt_info: dict[str, Any] | None = None
    architecture: dict[str, Any] | None = None

    if config.run_type in BASELINE_TYPES:
        prompt_info = {
            "system_prompt": (
                results[0]["input"]["system_prompt"] if results else None
            ),
            "prompt_template": _PROMPT_TEMPLATES.get(config.run_type),
            "template_name": config.run_label,
        }

    elif config.run_type == "M1":
        specialist_prompts = {}
        for name, agent in specialists.items():  # type: ignore[possibly-undefined]
            pt = agent.prompt_template
            specialist_prompts[name] = {
                "description": pt.description,
                "version": pt.version,
                "system_prompt": pt.system.strip(),
                "categories": agent.config.categories,
                "category_count": len(agent.config.categories),
            }
        architecture = {
            "type": "multi_agent",
            "description": (
                "LangGraph orchestrator uses LLM reasoning to route "
                "questions to specialists, then validation"
            ),
            "workflow": ["route (LLM)", "specialist", "validate", "finalize"],
            "specialists": list(specialists.keys()),  # type: ignore[possibly-undefined]
            "validation_enabled": orchestrator.validation_agent is not None,  # type: ignore[possibly-undefined]
            "routing_table": CATEGORY_ROUTING,
            "specialist_prompts": specialist_prompts,
        }

    elif config.run_type == "M6":
        architecture = {
            "type": "single_agent_ablation",
            "description": (
                "Single agent with combined specialist prompts "
                "(architecture ablation)"
            ),
            "workflow": ["combined_prompt"],
            "system_prompt": M6_SYSTEM_PROMPT,
        }

    # ── 8. Save ──
    summary_path, diag_path = save_experiment(
        run_id=run_id,
        results=results,
        metrics=metrics,
        per_tier=per_tier,
        diag_summary=diag_summary,
        diagnostics=diagnostics,
        model_key=config.model_key,
        config=model_cfg,
        run_type=config.run_type,
        run_label=config.run_label,
        intermediate_path=intermediate_path,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        samples_per_tier=config.samples_per_tier,
        max_contract_chars=config.max_contract_chars,
        include_negative=config.include_negative,
        prompt=prompt_info,
        architecture=architecture,
        is_official=config.is_official,
    )

    elapsed = time.monotonic() - t_start

    return ExperimentResult(
        run_id=run_id,
        config=config,
        summary_path=summary_path,
        diagnostics_path=diag_path,
        intermediate_path=intermediate_path,
        metrics=metrics,
        per_tier=per_tier,
        n_samples=len(results),
        n_failures=len(failures),
        elapsed_seconds=elapsed,
    )


# ── Batch convenience wrapper ───────────────────────────────────────────────


async def run_batch(
    configs: list[ExperimentConfig],
    *,
    samples: list[CUADSample] | None = None,
    output_dir: Path | str = Path("experiments/results"),
    parallel: bool = True,
) -> list[ExperimentResult]:
    """Run multiple experiment configs and print a summary table.

    Loads CUAD samples once and shares them across all runs. By default runs
    concurrently via ``asyncio.gather``. Set ``parallel=False`` to run
    sequentially if you need to avoid rate-limit contention on the same
    provider.

    Args:
        configs: List of experiment configurations.
        samples: Pre-loaded samples. If None, loads once using the first
            config's sampling parameters.
        output_dir: Directory for result files.
        parallel: If True, run all configs concurrently. Only safe when
            configs use different API providers.

    Returns:
        List of ExperimentResult (one per config). Failed runs are omitted.

    Notebook usage::

        from src.experiments.pipeline import ExperimentConfig, run_batch

        # Sequential (safe default)
        results = await run_batch([
            ExperimentConfig(model_key="gpt-4.1-mini", run_type="B1"),
            ExperimentConfig(model_key="gpt-4.1-mini", run_type="B4"),
        ])

        # Parallel across providers (advanced)
        results = await run_batch([
            ExperimentConfig(model_key="gpt-4.1-mini",    run_type="B1"),
            ExperimentConfig(model_key="claude-sonnet-4",  run_type="B1"),
            ExperimentConfig(model_key="gemini-2.5-flash", run_type="B1"),
        ], parallel=True)
    """
    import asyncio
    import time

    output_dir = Path(output_dir)
    n = len(configs)

    print(f"\nBatch: {n} experiment{'s' if n != 1 else ''}")
    for i, c in enumerate(configs, 1):
        print(f"  {i}. {c.run_type} / {c.model_key}")
    print()

    # Load samples once
    if samples is None:
        ref = configs[0]
        print("Loading CUAD data and sampling...")
        t0 = time.monotonic()
        samples = load_and_select_samples(
            samples_per_tier=ref.samples_per_tier,
            include_negative=ref.include_negative,
            max_contract_chars=ref.max_contract_chars,
        )
        print(f"  {len(samples)} samples selected in {time.monotonic() - t0:.1f}s\n")

    completed: list[ExperimentResult] = []
    failed: list[tuple[ExperimentConfig, str]] = []

    if parallel:
        # Run all concurrently
        tasks = [
            run_experiment_pipeline(cfg, samples=samples, output_dir=output_dir)
            for cfg in configs
        ]
        settled = await asyncio.gather(*tasks, return_exceptions=True)
        for cfg, outcome in zip(configs, settled):
            if isinstance(outcome, BaseException):
                error_msg = f"{type(outcome).__name__}: {outcome}"
                print(f"\n  FAILED {cfg.run_type}/{cfg.model_key}: {error_msg}\n")
                failed.append((cfg, error_msg))
            else:
                completed.append(outcome)
    else:
        # Run sequentially
        for i, cfg in enumerate(configs, 1):
            print(f"\n{'#'*60}")
            print(f"  [{i}/{n}] {cfg.run_type} / {cfg.model_key}")
            print(f"{'#'*60}")
            try:
                result = await run_experiment_pipeline(
                    config=cfg, samples=samples, output_dir=output_dir,
                )
                completed.append(result)
            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                print(f"\n  FAILED: {error_msg}\n")
                failed.append((cfg, error_msg))

    # Summary table
    _print_batch_summary(completed, failed, n)

    return completed


def _print_batch_summary(
    completed: list[ExperimentResult],
    failed: list[tuple[ExperimentConfig, str]],
    total: int,
) -> None:
    """Print a summary table after a batch run."""
    print(f"\n{'='*80}")
    print("  BATCH SUMMARY")
    print(f"{'='*80}\n")

    if completed:
        print(
            f"  {'Type':<6} {'Model':<25} {'F1':>6} {'F2':>6} "
            f"{'Jaccard':>8} {'Lazy%':>6} {'Cost':>8} {'Time':>7}"
        )
        print(
            f"  {'-'*6} {'-'*25} {'-'*6} {'-'*6} "
            f"{'-'*8} {'-'*6} {'-'*8} {'-'*7}"
        )

        for r in completed:
            m = r.metrics
            cost = m.get("total_cost_usd", 0.0)
            mins = r.elapsed_seconds / 60
            print(
                f"  {r.config.run_type:<6} {r.config.model_key:<25} "
                f"{m.get('f1', 0):.4f} {m.get('f2', 0):.4f} "
                f"{m.get('avg_jaccard', 0):.4f}  "
                f"{m.get('laziness_rate', 0)*100:5.1f} "
                f"${cost:7.3f} {mins:5.1f}m"
            )

    if failed:
        print(f"\n  FAILED ({len(failed)}):")
        for cfg, err in failed:
            print(f"    {cfg.run_type} / {cfg.model_key}: {err}")

    total_time = sum(r.elapsed_seconds for r in completed)
    print(
        f"\n  Completed: {len(completed)}/{total}  |  "
        f"Total time: {total_time/60:.1f}m"
    )
    print()


# ── Extract function factories ──────────────────────────────────────────────


def _make_baseline_extract_fn(
    config: ExperimentConfig,
    diagnostics: ModelDiagnostics,
):
    """Build an async extract_fn for B1 or B4 baselines."""

    async def extract_fn(sample: CUADSample) -> ExtractionOutput:
        system_prompt, user_message = _build_baseline_messages(
            sample, config.run_type
        )
        messages = [{"role": "user", "content": user_message}]

        raw_response, usage = await model_invoke(
            model_key=config.model_key,
            messages=messages,
            system=system_prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            diagnostics=diagnostics,
            agent_name=config.run_label,
            category=sample.category,
        )

        result = _parse_baseline_response(
            raw_response, sample.category, config.run_type
        )

        return ExtractionOutput(
            extracted_clauses=result.extracted_clauses,
            raw_response=raw_response,
            reasoning=result.reasoning,
            confidence=result.confidence,
            system_prompt=system_prompt,
            user_message_length=len(user_message),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_tokens", 0),
            cache_creation_tokens=getattr(usage, "cache_creation_tokens", 0),
        )

    return extract_fn


def _make_m1_extract_fn(config: ExperimentConfig, *, run_id: str):
    """Build an async extract_fn for M1 (full multi-agent).

    Returns (diagnostics, extract_fn, orchestrator, specialists).
    """
    from src.agents import (
        IPCommercialAgent,
        Orchestrator,
        RiskLiabilityAgent,
        TemporalRenewalAgent,
    )

    run_mode = "official" if config.is_official else "test"
    diagnostics = ModelDiagnostics(experiment_id=run_id, run_mode=run_mode)

    risk_cfg = AgentConfig(
        name="risk_liability",
        model_key=config.model_key,
        prompt_name="risk_liability",
    )
    temporal_cfg = AgentConfig(
        name="temporal_renewal",
        model_key=config.model_key,
        prompt_name="temporal_renewal",
    )
    ip_cfg = AgentConfig(
        name="ip_commercial",
        model_key=config.model_key,
        prompt_name="ip_commercial",
    )

    specialists = {
        "risk_liability": RiskLiabilityAgent(
            config=risk_cfg, diagnostics=diagnostics
        ),
        "temporal_renewal": TemporalRenewalAgent(
            config=temporal_cfg, diagnostics=diagnostics
        ),
        "ip_commercial": IPCommercialAgent(
            config=ip_cfg, diagnostics=diagnostics
        ),
    }

    orchestrator = Orchestrator(
        specialists=specialists,
        validation_agent=None,
        config=AgentConfig(name="orchestrator", model_key=config.model_key),
        diagnostics=diagnostics,
    )

    async def extract_fn(sample: CUADSample) -> ExtractionOutput:
        n_calls_before = len(diagnostics.calls)

        result, trace = await orchestrator.extract(
            contract_text=sample.contract_text,
            category=sample.category,
            question=sample.question,
        )

        system_prompt = (
            "M1 multi-agent (orchestrator -> specialist -> validation)"
        )
        user_message = (
            f"Category: {sample.category}\nQuestion: {sample.question}"
        )

        recent_calls = diagnostics.calls[n_calls_before:]
        agg_input = sum(c.usage.input_tokens for c in recent_calls)
        agg_output = sum(c.usage.output_tokens for c in recent_calls)
        trace_nodes = [c.agent_name for c in recent_calls]

        # Extract routing info from trace
        route_entry = next((t for t in trace if t.get("node") == "route"), None)
        agent_routed_to = route_entry.get("routed_to") if route_entry else None
        routing_reasoning = route_entry.get("routing_reasoning") if route_entry else None
        routing_correct = route_entry.get("routing_correct") if route_entry else None

        return ExtractionOutput(
            extracted_clauses=result.extracted_clauses,
            raw_response=result.reasoning,
            reasoning=result.reasoning,
            confidence=result.confidence,
            system_prompt=system_prompt,
            user_message_length=len(user_message),
            input_tokens=agg_input,
            output_tokens=agg_output,
            trace_nodes=trace_nodes,
            agent_routed_to=agent_routed_to,
            routing_reasoning=routing_reasoning,
            routing_correct=routing_correct,
        )

    return diagnostics, extract_fn, orchestrator, specialists


def _make_m6_extract_fn(config: ExperimentConfig, *, run_id: str):
    """Build an async extract_fn for M6 (combined prompts ablation).

    Returns (diagnostics, extract_fn, m6_baseline).
    """
    run_mode = "official" if config.is_official else "test"
    diagnostics = ModelDiagnostics(experiment_id=run_id, run_mode=run_mode)

    m6_baseline = CombinedPromptsBaseline(
        config=AgentConfig(name="combined_prompts", model_key=config.model_key),
        diagnostics=diagnostics,
    )

    async def extract_fn(sample: CUADSample) -> ExtractionOutput:
        domain = _get_domain(sample.category)
        domain_expertise = _DOMAIN_EXPERTISE.get(domain, "General contract analysis.")

        system_prompt = M6_SYSTEM_PROMPT
        user_message = M6_USER_TEMPLATE.format(
            domain=domain.replace("_", " ").title(),
            domain_expertise=domain_expertise,
            category=sample.category,
            indicators=_get_indicators(sample.category),
            contract_text=sample.contract_text,
            question=sample.question,
        )
        messages = [{"role": "user", "content": user_message}]

        raw_response, usage = await model_invoke(
            model_key=config.model_key,
            messages=messages,
            system=system_prompt,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            diagnostics=diagnostics,
            agent_name="combined_prompts",
            category=sample.category,
        )

        result = m6_baseline._cot_parser.parse_response(raw_response)
        result.category = sample.category

        return ExtractionOutput(
            extracted_clauses=result.extracted_clauses,
            raw_response=raw_response,
            reasoning=result.reasoning,
            confidence=result.confidence,
            system_prompt=system_prompt,
            user_message_length=len(user_message),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_read_tokens=getattr(usage, "cache_read_tokens", 0),
            cache_creation_tokens=getattr(usage, "cache_creation_tokens", 0),
        )

    return diagnostics, extract_fn, m6_baseline
