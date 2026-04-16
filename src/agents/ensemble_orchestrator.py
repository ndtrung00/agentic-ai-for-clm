"""M8: Ensemble multi-agent orchestrator using LangGraph.

Two agents (conservative B4 + aggressive specialist) extract in parallel.
A merge node detects agreement/disagreement.
A resolver agent adjudicates disagreements with conservative bias.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.agents.base import ExtractionResult
from src.agents.orchestrator import CATEGORY_ROUTING
from src.agents.validation import ValidationAgent
from src.baselines.chain_of_thought import (
    COT_SYSTEM_PROMPT,
    COT_USER_TEMPLATE,
    ChainOfThoughtBaseline,
)
from src.models.client import get_observe_decorator, invoke_model
from src.models.diagnostics import ModelDiagnostics
from src.prompts.registry import get_prompt

observe = get_observe_decorator()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


@dataclass
class EnsembleGraphState:
    """State that flows through the M8 ensemble LangGraph workflow.

    Tracks results from both conservative and aggressive agents,
    merge analysis, and the final resolved output.
    """

    # Input
    contract_text: str = ""
    category: str = ""
    question: str = ""

    # Conservative agent result
    conservative_result: ExtractionResult | None = None

    # Aggressive agent result
    aggressive_result: ExtractionResult | None = None

    # Merge analysis
    agreement_type: str = ""  # "both_empty", "both_match", "disagree"
    needs_resolution: bool = False

    # Output
    final_result: ExtractionResult | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """Collapse whitespace for substring comparison."""
    return " ".join(text.split()).lower()


def _check_clause_overlap(
    result_a: ExtractionResult,
    result_b: ExtractionResult,
) -> bool:
    """Check whether any clause from one result overlaps with the other.

    Two clauses "overlap" when one is a substring of the other after
    whitespace normalisation.

    Args:
        result_a: First extraction result.
        result_b: Second extraction result.

    Returns:
        True if at least one clause pair overlaps.
    """
    for clause_a in result_a.extracted_clauses:
        norm_a = _normalize(clause_a)
        for clause_b in result_b.extracted_clauses:
            norm_b = _normalize(clause_b)
            if norm_a in norm_b or norm_b in norm_a:
                return True
    return False


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class EnsembleOrchestrator:
    """M8: Ensemble multi-agent using LangGraph.

    Two agents (conservative B4 + aggressive specialist) extract in parallel.
    A merge node detects agreement/disagreement.
    A resolver agent adjudicates disagreements with conservative bias.

    Workflow::

        START -> extract_both -> merge -> [resolve | grounding] -> grounding -> finalize -> END
    """

    def __init__(
        self,
        model_key: str,
        diagnostics: ModelDiagnostics | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        """Initialise the ensemble orchestrator.

        Args:
            model_key: Key from the model registry (e.g. ``"claude-sonnet-4"``).
            diagnostics: Optional diagnostics tracker for token/cost/latency.
            temperature: Sampling temperature for all LLM calls.
            max_tokens: Maximum tokens for LLM responses.
        """
        self.model_key = model_key
        self.diagnostics = diagnostics
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.validation_agent = ValidationAgent()
        self._b4_parser = ChainOfThoughtBaseline()

        # Load specialist prompts for the aggressive agent
        self._specialist_prompts = {
            "risk_liability": get_prompt("risk_liability"),
            "temporal_renewal": get_prompt("temporal_renewal"),
            "ip_commercial": get_prompt("ip_commercial"),
        }

        # Load resolver prompt
        self._resolver_prompt = get_prompt("ensemble_resolver")

        self._graph = self._build_graph()
        self._compiled_graph = self._graph.compile()

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.

        Uses a single ``extract_both`` node that runs both agents
        (conservative and aggressive) concurrently via ``asyncio.gather``.
        This avoids fan-out complexity with dataclass-based state.

        Returns:
            Configured StateGraph.
        """
        graph = StateGraph(EnsembleGraphState)

        graph.add_node("extract_both", self._extract_both_node)
        graph.add_node("merge", self._merge_node)
        graph.add_node("resolve", self._resolve_node)
        graph.add_node("grounding", self._grounding_node)
        graph.add_node("finalize", self._finalize_node)

        graph.add_edge(START, "extract_both")
        graph.add_edge("extract_both", "merge")

        graph.add_conditional_edges(
            "merge",
            self._merge_route,
            {
                "resolve": "resolve",
                "grounding": "grounding",
            },
        )

        graph.add_edge("resolve", "grounding")
        graph.add_edge("grounding", "finalize")
        graph.add_edge("finalize", END)

        return graph

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    async def _extract_both_node(self, state: EnsembleGraphState) -> dict[str, Any]:
        """Run conservative (B4) and aggressive (specialist) agents concurrently.

        Args:
            state: Current graph state.

        Returns:
            Updated state dict with both agent results and trace entries.
        """
        conservative_result, aggressive_result = await asyncio.gather(
            self._run_conservative(state),
            self._run_aggressive(state),
        )

        trace_entry = {
            "node": "extract_both",
            "category": state.category,
            "conservative_clauses": len(conservative_result.extracted_clauses),
            "aggressive_clauses": len(aggressive_result.extracted_clauses),
        }

        return {
            "conservative_result": conservative_result,
            "aggressive_result": aggressive_result,
            "trace": state.trace + [trace_entry],
        }

    def _merge_node(self, state: EnsembleGraphState) -> dict[str, Any]:
        """Deterministic merge: compare conservative and aggressive results.

        Sets ``agreement_type`` and ``needs_resolution``, and picks a
        ``final_result`` when the agents agree.

        Args:
            state: Current graph state.

        Returns:
            Updated state dict with merge analysis.
        """
        conservative = state.conservative_result
        aggressive = state.aggressive_result

        conservative_empty = not conservative or not conservative.extracted_clauses
        aggressive_empty = not aggressive or not aggressive.extracted_clauses

        if conservative_empty and aggressive_empty:
            agreement_type = "both_empty"
            needs_resolution = False
            final_result = ExtractionResult(
                extracted_clauses=[],
                reasoning="Both agents found no relevant clauses.",
                confidence=1.0,
                category=state.category,
            )
        elif not conservative_empty and not aggressive_empty:
            has_overlap = _check_clause_overlap(conservative, aggressive)
            if has_overlap:
                agreement_type = "both_match"
                needs_resolution = False
                # Use conservative result (higher precision)
                final_result = conservative
            else:
                agreement_type = "disagree"
                needs_resolution = True
                final_result = None
        else:
            # One found clauses, the other didn't -- disagreement
            agreement_type = "disagree"
            needs_resolution = True
            final_result = None

        trace_entry = {
            "node": "merge",
            "agreement_type": agreement_type,
            "needs_resolution": needs_resolution,
        }

        result: dict[str, Any] = {
            "agreement_type": agreement_type,
            "needs_resolution": needs_resolution,
            "trace": state.trace + [trace_entry],
        }
        if final_result is not None:
            result["final_result"] = final_result
        return result

    @staticmethod
    def _merge_route(state: EnsembleGraphState) -> str:
        """Route after merge: resolve disagreements, otherwise ground.

        Args:
            state: Current graph state.

        Returns:
            Next node name.
        """
        return "resolve" if state.needs_resolution else "grounding"

    async def _resolve_node(self, state: EnsembleGraphState) -> dict[str, Any]:
        """Adjudicate disagreements between conservative and aggressive agents.

        Calls the resolver LLM with both agents' outputs and the original
        contract, then parses the response into a final ExtractionResult.

        Args:
            state: Current graph state.

        Returns:
            Updated state dict with resolved ``final_result``.
        """
        # Format clauses for the prompt
        conservative_clauses: str
        aggressive_clauses: str

        if state.conservative_result and state.conservative_result.extracted_clauses:
            conservative_clauses = json.dumps(
                state.conservative_result.extracted_clauses, indent=2
            )
        else:
            conservative_clauses = "None found"

        if state.aggressive_result and state.aggressive_result.extracted_clauses:
            aggressive_clauses = json.dumps(
                state.aggressive_result.extracted_clauses, indent=2
            )
        else:
            aggressive_clauses = "None found"

        conservative_reasoning = (
            state.conservative_result.reasoning
            if state.conservative_result
            else "N/A"
        )
        aggressive_reasoning = (
            state.aggressive_result.reasoning
            if state.aggressive_result
            else "N/A"
        )

        try:
            system_prompt, user_prompt = self._resolver_prompt.format(
                category=state.category,
                question=state.question,
                contract_text=state.contract_text,
                conservative_clauses=conservative_clauses,
                conservative_reasoning=conservative_reasoning,
                aggressive_clauses=aggressive_clauses,
                aggressive_reasoning=aggressive_reasoning,
            )

            messages = [{"role": "user", "content": user_prompt}]

            raw_response, _usage = await invoke_model(
                model_key=self.model_key,
                messages=messages,
                system=system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                json_mode=True,
                diagnostics=self.diagnostics,
                agent_name="m8_resolver",
                category=state.category,
            )

            data = self._parse_json_response(raw_response)
            final_result = self._result_from_dict(data, state.category)

            trace_entry = {
                "node": "resolve",
                "category": state.category,
                "resolved_clauses": len(final_result.extracted_clauses),
                "raw_response_preview": raw_response[:200],
            }

            return {
                "final_result": final_result,
                "trace": state.trace + [trace_entry],
            }

        except Exception as e:
            logger.error("Resolver failed for %s: %s", state.category, e)
            # Fallback: prefer whichever agent found clauses, or aggressive
            fallback = state.aggressive_result or state.conservative_result
            if fallback is None:
                fallback = ExtractionResult(
                    extracted_clauses=[],
                    reasoning=f"Resolver error: {e}",
                    confidence=0.0,
                    category=state.category,
                )

            trace_entry = {
                "node": "resolve",
                "category": state.category,
                "error": str(e),
                "fallback": "aggressive" if state.aggressive_result else "conservative",
            }

            return {
                "final_result": fallback,
                "trace": state.trace + [trace_entry],
            }

    async def _grounding_node(self, state: EnsembleGraphState) -> dict[str, Any]:
        """Validate the final result for grounding.

        Args:
            state: Current graph state.

        Returns:
            Updated state dict with grounding-checked ``final_result``.
        """
        trace_entry: dict[str, Any] = {"node": "grounding"}

        if state.final_result is None:
            trace_entry["skipped"] = True
            return {"trace": state.trace + [trace_entry]}

        try:
            validated = await self.validation_agent.verify(
                extraction_result=state.final_result,
                contract_text=state.contract_text,
                category=state.category,
            )
            trace_entry["grounding_checked"] = True
            trace_entry["clauses_before"] = len(state.final_result.extracted_clauses)
            trace_entry["clauses_after"] = len(validated.extracted_clauses)

            return {
                "final_result": validated,
                "trace": state.trace + [trace_entry],
            }
        except Exception as e:
            trace_entry["error"] = str(e)
            return {"trace": state.trace + [trace_entry]}

    def _finalize_node(self, state: EnsembleGraphState) -> dict[str, Any]:
        """Ensure a final result is set.

        Args:
            state: Current graph state.

        Returns:
            Updated state dict.
        """
        trace_entry: dict[str, Any] = {
            "node": "finalize",
            "has_result": state.final_result is not None,
            "has_error": state.error is not None,
            "agreement_type": state.agreement_type,
        }

        if state.final_result is None:
            # Last-resort fallback
            fallback = (
                state.conservative_result
                or state.aggressive_result
                or ExtractionResult(
                    extracted_clauses=[],
                    reasoning="No result produced by ensemble.",
                    confidence=0.0,
                    category=state.category,
                )
            )
            return {
                "final_result": fallback,
                "trace": state.trace + [trace_entry],
            }

        return {"trace": state.trace + [trace_entry]}

    # ------------------------------------------------------------------
    # Agent helpers
    # ------------------------------------------------------------------

    async def _run_conservative(self, state: EnsembleGraphState) -> ExtractionResult:
        """Run the conservative agent (B4 Chain-of-Thought).

        Args:
            state: Current graph state.

        Returns:
            ExtractionResult from B4 prompting.
        """
        user_message = COT_USER_TEMPLATE.format(
            contract_text=state.contract_text,
            question=state.question,
        )
        messages = [{"role": "user", "content": user_message}]

        try:
            raw_response, _usage = await invoke_model(
                model_key=self.model_key,
                messages=messages,
                system=COT_SYSTEM_PROMPT,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                diagnostics=self.diagnostics,
                agent_name="m8_conservative",
                category=state.category,
            )

            result = self._b4_parser.parse_response(raw_response)
            result.category = state.category
            return result

        except Exception as e:
            logger.error("Conservative agent failed for %s: %s", state.category, e)
            return ExtractionResult(
                extracted_clauses=[],
                reasoning=f"Conservative agent error: {e}",
                confidence=0.0,
                category=state.category,
            )

    async def _run_aggressive(self, state: EnsembleGraphState) -> ExtractionResult:
        """Run the aggressive agent (domain specialist).

        Routes to the correct specialist via ``CATEGORY_ROUTING`` and
        calls ``invoke_model`` with the specialist prompt and JSON mode.

        Args:
            state: Current graph state.

        Returns:
            ExtractionResult from specialist prompting.
        """
        # Determine domain
        domain = CATEGORY_ROUTING.get(state.category)
        if domain is None:
            cat_lower = state.category.lower()
            for key, val in CATEGORY_ROUTING.items():
                if key.lower() == cat_lower:
                    domain = val
                    break
        if domain is None:
            domain = "risk_liability"  # fallback

        prompt = self._specialist_prompts[domain]
        indicators = prompt.format_indicators(state.category)

        try:
            system_prompt, user_prompt = prompt.format(
                category=state.category,
                indicators=indicators,
                contract_text=state.contract_text,
                question=state.question,
            )

            messages = [{"role": "user", "content": user_prompt}]

            raw_response, _usage = await invoke_model(
                model_key=self.model_key,
                messages=messages,
                system=system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                json_mode=True,
                diagnostics=self.diagnostics,
                agent_name="m8_aggressive",
                category=state.category,
            )

            data = self._parse_json_response(raw_response)
            result = self._result_from_dict(data, state.category)
            return result

        except Exception as e:
            logger.error("Aggressive agent failed for %s: %s", state.category, e)
            return ExtractionResult(
                extracted_clauses=[],
                reasoning=f"Aggressive agent error: {e}",
                confidence=0.0,
                category=state.category,
            )

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(response: str) -> dict[str, Any]:
        """Extract JSON from a model response.

        Tries direct parse, markdown code-block extraction, and raw
        JSON-object extraction in order.

        Args:
            response: Raw model response text.

        Returns:
            Parsed dictionary, or empty dict on failure.
        """
        # Try direct parse
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding a raw JSON object
        match = re.search(r"\{[\s\S]*\}", response)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return {}

    @staticmethod
    def _result_from_dict(data: dict[str, Any], category: str) -> ExtractionResult:
        """Build an ExtractionResult from a parsed JSON dict.

        Handles the ``no_clause_found`` flag: when True, returns an empty
        extraction regardless of what ``extracted_clauses`` contains.

        Args:
            data: Parsed response dictionary.
            category: The CUAD category being extracted.

        Returns:
            ExtractionResult instance.
        """
        if data.get("no_clause_found", False):
            return ExtractionResult(
                extracted_clauses=[],
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", 1.0),
                category_indicators_found=data.get("category_indicators_found", []),
                category=category,
            )

        return ExtractionResult(
            extracted_clauses=data.get("extracted_clauses", []),
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 0.0),
            category_indicators_found=data.get("category_indicators_found", []),
            category=category,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @observe(name="ensemble_orchestrator.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> tuple[ExtractionResult, list[dict[str, Any]]]:
        """Run the full ensemble extraction workflow.

        Args:
            contract_text: The full contract text.
            category: The CUAD category to extract.
            question: The question prompt for this category.

        Returns:
            Tuple of (extraction_result, trace). Trace contains per-node
            execution history for explainability.
        """
        initial_state = EnsembleGraphState(
            contract_text=contract_text,
            category=category,
            question=question,
        )

        final_state = await self._compiled_graph.ainvoke(initial_state)

        trace = final_state.get("trace", [])

        if final_state.get("error"):
            return (
                ExtractionResult(
                    extracted_clauses=[],
                    reasoning=f"Error: {final_state['error']}",
                    confidence=0.0,
                    category=category,
                ),
                trace,
            )

        result = final_state.get("final_result")
        if result is None:
            return (
                ExtractionResult(
                    extracted_clauses=[],
                    reasoning="No result produced by ensemble.",
                    confidence=0.0,
                    category=category,
                ),
                trace,
            )

        return result, trace
