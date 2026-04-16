"""M7: Extract-then-Verify multi-agent orchestrator using LangGraph.

Pipeline: B4 extracts -> triage decides -> specialist verifies -> grounding check.

Architecture:
    START -> extract -> triage -> [verify OR finalize] -> grounding -> finalize -> END

The extractor uses the B4 (Chain-of-Thought) prompt and parser to produce an
initial extraction.  A deterministic triage node then decides whether
verification is needed:

- Clauses extracted -> verify relevance with specialist indicators.
- No clauses AND rare category -> laziness recovery attempt.
- No clauses AND common/moderate category -> skip to finalize.

The verifier loads domain-specific indicators from the specialist YAML prompts
and calls the LLM with a structured verification prompt.  Finally a non-LLM
grounding check (via ValidationAgent) ensures all clauses appear verbatim in
the contract.
"""

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

# ── Tier constants ───────────────────────────────────────────────────────────

RARE_CATEGORIES = {
    "Uncapped Liability",
    "Joint Ip Ownership",
    "Notice Period To Terminate Renewal",
    "Volume Restriction",
    "Minimum Commitment",
    "Revenue/Profit Sharing",
    "Price Restrictions",
    "Most Favored Nation",
    "Competitive Restriction Exception",
    "Third Party Beneficiary",
    "Affiliate License-Licensor",
    "Affiliate License-Licensee",
    "Unlimited/All-You-Can-Eat-License",
    "Source Code Escrow",
    "Liquidated Damages",
    "Covenant Not To Sue",
    "Non-Disparagement",
}

# Pre-compute lower-cased set for case-insensitive matching
_RARE_CATEGORIES_LOWER = {c.lower() for c in RARE_CATEGORIES}


# ── Graph state ──────────────────────────────────────────────────────────────


@dataclass
class VerifyGraphState:
    """State that flows through the M7 Extract-then-Verify workflow.

    Accumulates results as the pipeline progresses from extraction
    through optional verification to grounding and finalization.
    """

    # Input
    contract_text: str = ""
    category: str = ""
    question: str = ""

    # Extraction (stage 1)
    extractor_result: ExtractionResult | None = None

    # Triage
    needs_verification: bool = False
    verification_reason: str = ""  # "has_clauses", "rare_laziness_check", "skipped"

    # Verification (stage 2)
    verified_result: ExtractionResult | None = None
    verification_action: str = ""  # "confirmed", "filtered", "recovered", "empty"

    # Output
    final_result: ExtractionResult | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None


# ── Orchestrator ─────────────────────────────────────────────────────────────


class VerifyOrchestrator:
    """M7: Extract-then-Verify using LangGraph.

    Pipeline: B4 extracts -> triage decides -> specialist verifies -> grounding check.

    This orchestrator uses a two-stage approach:
    1. A Chain-of-Thought extractor (B4) performs initial clause extraction.
    2. A triage node decides whether verification is needed.
    3. If needed, a verifier LLM call uses domain-specific indicators to
       confirm, filter, or recover clauses.
    4. A grounding check ensures all final clauses appear verbatim in the contract.
    """

    def __init__(
        self,
        model_key: str,
        diagnostics: ModelDiagnostics | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> None:
        """Initialize the verify orchestrator.

        Args:
            model_key: Key from the model registry (e.g. "claude-sonnet-4").
            diagnostics: Optional diagnostics tracker for token/cost/latency.
            temperature: LLM temperature for both extractor and verifier.
            max_tokens: Maximum tokens for LLM calls.
        """
        self.model_key = model_key
        self.diagnostics = diagnostics
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.validation_agent = ValidationAgent()

        # B4 parser instance (stateless, used only for parse_response)
        self._cot_parser = ChainOfThoughtBaseline()

        # Load verifier prompt template
        self._verifier_prompt = get_prompt("verifier")

        # Load specialist prompts for category indicators
        self._specialist_prompts = {
            "risk_liability": get_prompt("risk_liability"),
            "temporal_renewal": get_prompt("temporal_renewal"),
            "ip_commercial": get_prompt("ip_commercial"),
        }

        self._graph = self._build_graph()
        self._compiled_graph = self._graph.compile()

    # ── Graph construction ───────────────────────────────────────────────

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for the verify pipeline.

        Returns:
            Configured StateGraph with extract -> triage -> verify/finalize flow.
        """
        graph = StateGraph(VerifyGraphState)

        # Add nodes
        graph.add_node("extract", self._extract_node)
        graph.add_node("triage", self._triage_node)
        graph.add_node("verify", self._verify_node)
        graph.add_node("grounding", self._grounding_node)
        graph.add_node("finalize", self._finalize_node)

        # Add edges
        graph.add_edge(START, "extract")
        graph.add_edge("extract", "triage")

        # Conditional routing from triage
        graph.add_conditional_edges(
            "triage",
            self._triage_route,
            {
                "verify": "verify",
                "finalize": "finalize",
            },
        )

        graph.add_edge("verify", "grounding")
        graph.add_edge("grounding", "finalize")
        graph.add_edge("finalize", END)

        return graph

    # ── Node implementations ─────────────────────────────────────────────

    async def _extract_node(self, state: VerifyGraphState) -> dict[str, Any]:
        """Stage 1: Extract clauses using B4 Chain-of-Thought prompting.

        Calls invoke_model with the B4 system/user prompts and parses
        the response using ChainOfThoughtBaseline.parse_response().

        Args:
            state: Current graph state.

        Returns:
            Updated state with extractor_result populated.
        """
        trace_entry: dict[str, Any] = {
            "node": "extract",
            "category": state.category,
        }

        try:
            user_message = COT_USER_TEMPLATE.format(
                contract_text=state.contract_text,
                question=state.question,
            )
            messages = [{"role": "user", "content": user_message}]

            raw_response, _usage = await invoke_model(
                model_key=self.model_key,
                messages=messages,
                system=COT_SYSTEM_PROMPT,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                diagnostics=self.diagnostics,
                agent_name="m7_extractor",
                category=state.category,
            )

            result = self._cot_parser.parse_response(raw_response)
            result.category = state.category

            trace_entry["extracted_count"] = len(result.extracted_clauses)
            trace_entry["confidence"] = result.confidence

            return {
                "extractor_result": result,
                "trace": state.trace + [trace_entry],
            }

        except Exception as e:
            logger.error("M7 extraction failed for %s: %s", state.category, e)
            trace_entry["error"] = str(e)
            fallback = ExtractionResult(
                extracted_clauses=[],
                reasoning=f"Extraction error: {e}",
                confidence=0.0,
                category=state.category,
            )
            return {
                "extractor_result": fallback,
                "error": f"Extraction failed: {e}",
                "trace": state.trace + [trace_entry],
            }

    def _triage_node(self, state: VerifyGraphState) -> dict[str, Any]:
        """Deterministic triage: decide whether verification is needed.

        Rules:
        1. Clauses were extracted -> verify relevance.
        2. No clauses AND rare category -> laziness recovery attempt.
        3. No clauses AND common/moderate -> skip to finalize.

        Args:
            state: Current graph state.

        Returns:
            Updated state with needs_verification and verification_reason.
        """
        result = state.extractor_result
        has_clauses = bool(result and result.extracted_clauses)

        if has_clauses:
            needs_verification = True
            reason = "has_clauses"
        elif state.category.lower() in _RARE_CATEGORIES_LOWER:
            needs_verification = True
            reason = "rare_laziness_check"
        else:
            needs_verification = False
            reason = "skipped"

        trace_entry = {
            "node": "triage",
            "category": state.category,
            "has_clauses": has_clauses,
            "needs_verification": needs_verification,
            "verification_reason": reason,
        }

        return {
            "needs_verification": needs_verification,
            "verification_reason": reason,
            "trace": state.trace + [trace_entry],
        }

    @staticmethod
    def _triage_route(state: VerifyGraphState) -> str:
        """Route from triage to verify or finalize.

        Args:
            state: Current graph state.

        Returns:
            "verify" if verification is needed, "finalize" otherwise.
        """
        return "verify" if state.needs_verification else "finalize"

    async def _verify_node(self, state: VerifyGraphState) -> dict[str, Any]:
        """Stage 2: Verify or recover clauses using domain-specific indicators.

        Loads indicators from the appropriate specialist prompt, formats a
        verification prompt, and calls the LLM with json_mode=True.

        Args:
            state: Current graph state.

        Returns:
            Updated state with verified_result and verification_action.
        """
        trace_entry: dict[str, Any] = {
            "node": "verify",
            "category": state.category,
            "verification_reason": state.verification_reason,
        }

        try:
            # Resolve domain via CATEGORY_ROUTING (case-insensitive fallback)
            domain = CATEGORY_ROUTING.get(state.category)
            if domain is None:
                cat_lower = state.category.lower()
                for key, val in CATEGORY_ROUTING.items():
                    if key.lower() == cat_lower:
                        domain = val
                        break
            if domain is None:
                domain = "risk_liability"  # safe fallback
                logger.warning(
                    "Category %r not found in CATEGORY_ROUTING, defaulting to %s",
                    state.category,
                    domain,
                )

            # Get domain indicators for this category
            specialist_prompt = self._specialist_prompts.get(domain)
            if specialist_prompt is not None:
                indicators = specialist_prompt.format_indicators(state.category)
            else:
                indicators = "No specific indicators defined."

            # Format extractor clauses for the verifier prompt
            extractor_result = state.extractor_result
            if extractor_result and extractor_result.extracted_clauses:
                extractor_clauses = json.dumps(
                    extractor_result.extracted_clauses, indent=2
                )
            else:
                extractor_clauses = "None found"

            extractor_reasoning = (
                extractor_result.reasoning if extractor_result else "N/A"
            )

            # Format the verifier prompt (use human-readable domain name)
            domain_display = domain.replace("_", " ")
            system_prompt, user_prompt = self._verifier_prompt.format(
                category=state.category,
                question=state.question,
                indicators=indicators,
                extractor_clauses=extractor_clauses,
                extractor_reasoning=extractor_reasoning,
                contract_text=state.contract_text,
                domain=domain_display,
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
                agent_name="m7_verifier",
                category=state.category,
            )

            # Parse JSON response
            data = self._parse_json_response(raw_response)

            # Build ExtractionResult from parsed data
            verified_result = self._result_from_verifier(data, state.category)
            verification_action = data.get("verification_action", "confirmed")

            trace_entry["verification_action"] = verification_action
            trace_entry["extracted_count"] = len(verified_result.extracted_clauses)

            return {
                "verified_result": verified_result,
                "verification_action": verification_action,
                "trace": state.trace + [trace_entry],
            }

        except Exception as e:
            logger.error(
                "M7 verification failed for %s: %s", state.category, e
            )
            trace_entry["error"] = str(e)

            # On failure, pass through the extractor result
            return {
                "verified_result": state.extractor_result,
                "verification_action": "error",
                "trace": state.trace + [trace_entry],
            }

    async def _grounding_node(self, state: VerifyGraphState) -> dict[str, Any]:
        """Grounding check: ensure clauses appear verbatim in the contract.

        Uses ValidationAgent.verify() which is a non-LLM check.

        Args:
            state: Current graph state.

        Returns:
            Updated state with final_result after grounding verification.
        """
        trace_entry: dict[str, Any] = {
            "node": "grounding",
            "category": state.category,
        }

        # Use verified_result if available, otherwise extractor_result
        source_result = state.verified_result or state.extractor_result

        if source_result is None:
            trace_entry["skipped"] = True
            return {
                "trace": state.trace + [trace_entry],
            }

        try:
            grounded_result = await self.validation_agent.verify(
                extraction_result=source_result,
                contract_text=state.contract_text,
                category=state.category,
            )

            trace_entry["grounding_checked"] = True
            trace_entry["pre_grounding_count"] = len(source_result.extracted_clauses)
            trace_entry["post_grounding_count"] = len(
                grounded_result.extracted_clauses
            )

            return {
                "final_result": grounded_result,
                "trace": state.trace + [trace_entry],
            }

        except Exception as e:
            logger.error("M7 grounding failed for %s: %s", state.category, e)
            trace_entry["error"] = str(e)

            # On failure, use the ungrounded result
            return {
                "final_result": source_result,
                "trace": state.trace + [trace_entry],
            }

    def _finalize_node(self, state: VerifyGraphState) -> dict[str, Any]:
        """Finalize the extraction result.

        Falls back through the chain: final_result -> verified_result ->
        extractor_result -> empty result.

        Args:
            state: Current graph state.

        Returns:
            Final state updates with guaranteed final_result.
        """
        trace_entry: dict[str, Any] = {
            "node": "finalize",
            "category": state.category,
            "has_error": state.error is not None,
            "verification_action": state.verification_action or "none",
        }

        # Determine final result via fallback chain
        result = (
            state.final_result
            or state.verified_result
            or state.extractor_result
        )

        if result is not None:
            trace_entry["final_clause_count"] = len(result.extracted_clauses)
            return {
                "final_result": result,
                "trace": state.trace + [trace_entry],
            }

        # Nothing produced at all — return empty
        empty = ExtractionResult(
            extracted_clauses=[],
            reasoning="No result produced by any stage",
            confidence=0.0,
            category=state.category,
        )
        trace_entry["final_clause_count"] = 0
        return {
            "final_result": empty,
            "trace": state.trace + [trace_entry],
        }

    # ── Main extract method ──────────────────────────────────────────────

    @observe(name="verify_orchestrator.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> tuple[ExtractionResult, list[dict[str, Any]]]:
        """Run the full extract-then-verify workflow.

        Args:
            contract_text: The full contract text to analyze.
            category: The CUAD category to extract.
            question: The CUAD question prompt for this category.

        Returns:
            Tuple of (extraction_result, trace). Trace contains node execution
            history for explainability.
        """
        initial_state = VerifyGraphState(
            contract_text=contract_text,
            category=category,
            question=question,
        )

        final_state = await self._compiled_graph.ainvoke(initial_state)

        trace = final_state.get("trace", [])
        result = final_state.get("final_result")

        if result is None:
            result = ExtractionResult(
                extracted_clauses=[],
                reasoning="No result produced",
                confidence=0.0,
                category=category,
            )

        return result, trace

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(response: str) -> dict[str, Any]:
        """Parse JSON from a model response.

        Handles both clean JSON and JSON embedded in markdown code blocks.

        Args:
            response: Raw model response text.

        Returns:
            Parsed dictionary, or empty dict on failure.
        """
        # Try direct parse
        try:
            return json.loads(response.strip())
        except (json.JSONDecodeError, ValueError):
            pass

        # Try extracting from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except (json.JSONDecodeError, ValueError):
                pass

        # Try finding a raw JSON object
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except (json.JSONDecodeError, ValueError):
                pass

        logger.warning("Could not parse JSON from verifier response: %.200s", response)
        return {}

    @staticmethod
    def _result_from_verifier(
        data: dict[str, Any], category: str
    ) -> ExtractionResult:
        """Create ExtractionResult from parsed verifier response.

        Handles the ``no_clause_found`` flag: when True, returns an empty
        extraction regardless of what ``extracted_clauses`` contains.

        Args:
            data: Parsed JSON response from verifier.
            category: The CUAD category being extracted.

        Returns:
            ExtractionResult instance.
        """
        if data.get("no_clause_found", False):
            return ExtractionResult(
                extracted_clauses=[],
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", 1.0),
                category_indicators_found=data.get(
                    "category_indicators_found", []
                ),
                category=category,
            )

        return ExtractionResult(
            extracted_clauses=data.get("extracted_clauses", []),
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 0.0),
            category_indicators_found=data.get(
                "category_indicators_found", []
            ),
            category=category,
        )
