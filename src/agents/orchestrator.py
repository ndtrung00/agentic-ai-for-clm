"""Orchestrator agent using LangGraph for workflow management."""

import json
import re
from typing import Any
from dataclasses import dataclass, field

from src.models.client import get_observe_decorator, invoke_model

observe = get_observe_decorator()
from langgraph.graph import StateGraph, END, START

from src.agents.base import AgentConfig, ExtractionResult
from src.models.diagnostics import ModelDiagnostics


# ── Routing prompt ────────────────────────────────────────────────────────────

ROUTING_SYSTEM_PROMPT = """\
You are a routing agent for a contract analysis system. Your job is to read a \
question about a contract clause and decide which specialist should handle it.

Available specialists:

1. **risk_liability** — Expert in risk allocation, liability, and protective \
provisions. Covers: liability caps and uncapped liability, liquidated damages, \
insurance requirements, warranty duration, audit rights, non-disparagement, \
covenants not to sue, third-party beneficiaries, most favored nation clauses, \
change of control provisions, post-termination services, and minimum commitments.

2. **temporal_renewal** — Expert in temporal aspects, document identification, \
and contract lifecycle. Covers: document name and party identification, \
agreement/effective/expiration dates, renewal terms and notice periods for \
renewal termination, termination for convenience, anti-assignment provisions, \
rights of first refusal/offer/negotiation, and governing law.

3. **ip_commercial** — Expert in intellectual property rights and commercial \
restrictions. Covers: IP ownership and assignment, joint IP ownership, license \
grants (including transferability, affiliate licenses, unlimited/perpetual \
licenses), source code escrow, exclusivity, non-compete and non-solicitation \
clauses, competitive restriction exceptions, revenue/profit sharing, price \
restrictions, and volume restrictions.

Respond with ONLY a JSON object:
{"specialist": "<name>", "reasoning": "<brief explanation of why this specialist is the best fit>"}
Do not include any other text."""

# ── Ground truth routing (for accuracy measurement) ───────────────────────────

CATEGORY_ROUTING: dict[str, str] = {
    # Risk & Liability (13 categories)
    "Uncapped Liability": "risk_liability",
    "Cap On Liability": "risk_liability",
    "Liquidated Damages": "risk_liability",
    "Insurance": "risk_liability",
    "Warranty Duration": "risk_liability",
    "Audit Rights": "risk_liability",
    "Non-Disparagement": "risk_liability",
    "Covenant Not To Sue": "risk_liability",
    "Third Party Beneficiary": "risk_liability",
    "Most Favored Nation": "risk_liability",
    "Change Of Control": "risk_liability",
    "Post-Termination Services": "risk_liability",
    "Minimum Commitment": "risk_liability",
    # Temporal/Renewal (11 categories)
    "Document Name": "temporal_renewal",
    "Parties": "temporal_renewal",
    "Agreement Date": "temporal_renewal",
    "Effective Date": "temporal_renewal",
    "Expiration Date": "temporal_renewal",
    "Renewal Term": "temporal_renewal",
    "Notice Period To Terminate Renewal": "temporal_renewal",
    "Termination For Convenience": "temporal_renewal",
    "Anti-Assignment": "temporal_renewal",
    "Rofr/Rofo/Rofn": "temporal_renewal",
    "Governing Law": "temporal_renewal",
    # IP & Commercial (17 categories)
    "Ip Ownership Assignment": "ip_commercial",
    "Joint Ip Ownership": "ip_commercial",
    "License Grant": "ip_commercial",
    "Non-Transferable License": "ip_commercial",
    "Affiliate License-Licensor": "ip_commercial",
    "Affiliate License-Licensee": "ip_commercial",
    "Unlimited/All-You-Can-Eat-License": "ip_commercial",
    "Irrevocable Or Perpetual License": "ip_commercial",
    "Source Code Escrow": "ip_commercial",
    "Exclusivity": "ip_commercial",
    "Non-Compete": "ip_commercial",
    "No-Solicit Of Customers": "ip_commercial",
    "No-Solicit Of Employees": "ip_commercial",
    "Competitive Restriction Exception": "ip_commercial",
    "Revenue/Profit Sharing": "ip_commercial",
    "Price Restrictions": "ip_commercial",
    "Volume Restriction": "ip_commercial",
}


@dataclass
class GraphState:
    """State that flows through the LangGraph workflow.

    This state is passed between nodes and accumulates results
    as the workflow progresses.
    """
    # Input
    contract_text: str = ""
    category: str = ""
    question: str = ""

    # Routing
    specialist_name: str = ""

    # Extraction result from specialist
    extraction_result: ExtractionResult | None = None

    # Validation
    validated: bool = False
    validation_notes: str = ""

    # Final output
    final_result: ExtractionResult | None = None

    # Trace for explainability
    trace: list[dict[str, Any]] = field(default_factory=list)

    # Error handling
    error: str | None = None


class Orchestrator:
    """LangGraph-based orchestrator for multi-agent contract extraction.

    The workflow is:
    1. START -> route_to_specialist (LLM reasons about which specialist)
    2. route_to_specialist -> specialist_node (call appropriate specialist)
    3. specialist_node -> validation_node (validate extraction)
    4. validation_node -> END (return final result)
    """

    def __init__(
        self,
        specialists: dict[str, Any],  # BaseAgent instances
        validation_agent: Any | None = None,  # ValidationAgent instance
        config: AgentConfig | None = None,
        diagnostics: ModelDiagnostics | None = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            specialists: Dict mapping specialist names to agent instances.
            validation_agent: Optional validation agent for grounding checks.
            config: Optional orchestrator configuration.
            diagnostics: Optional diagnostics tracker for routing LLM calls.
        """
        self.specialists = specialists
        self.validation_agent = validation_agent
        self.config = config or AgentConfig(name="orchestrator")
        self.diagnostics = diagnostics
        self._graph = self._build_graph()
        self._compiled_graph = self._graph.compile()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.

        Returns:
            Configured StateGraph for the multi-agent workflow.
        """
        # Create graph with state schema
        graph = StateGraph(GraphState)

        # Add nodes
        graph.add_node("route", self._route_node)
        graph.add_node("risk_liability", self._make_specialist_node("risk_liability"))
        graph.add_node("temporal_renewal", self._make_specialist_node("temporal_renewal"))
        graph.add_node("ip_commercial", self._make_specialist_node("ip_commercial"))
        graph.add_node("validate", self._validation_node)
        graph.add_node("finalize", self._finalize_node)

        # Add edges
        graph.add_edge(START, "route")

        # Conditional routing based on category
        graph.add_conditional_edges(
            "route",
            self._get_specialist_route,
            {
                "risk_liability": "risk_liability",
                "temporal_renewal": "temporal_renewal",
                "ip_commercial": "ip_commercial",
                "error": "finalize",
            }
        )

        # All specialists go to validation
        graph.add_edge("risk_liability", "validate")
        graph.add_edge("temporal_renewal", "validate")
        graph.add_edge("ip_commercial", "validate")

        # Validation goes to finalize
        graph.add_edge("validate", "finalize")

        # Finalize goes to END
        graph.add_edge("finalize", END)

        return graph

    async def _route_node(self, state: GraphState) -> dict[str, Any]:
        """Route to the appropriate specialist via LLM reasoning.

        The orchestrator LLM reads the question and decides which specialist
        domain is most appropriate, without seeing the category label directly.

        Args:
            state: Current graph state.

        Returns:
            Updated state with specialist_name set.
        """
        category = state.category
        question = state.question

        # Ground truth for routing accuracy measurement
        expected_specialist = CATEGORY_ROUTING.get(category)

        # Ask the LLM to route based on the question
        messages = [{"role": "user", "content": f"Question: {question}"}]

        try:
            raw_response, _usage = await invoke_model(
                model_key=self.config.model_key,
                messages=messages,
                system=ROUTING_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=150,
                json_mode=True,
                diagnostics=self.diagnostics,
                agent_name="orchestrator_router",
                category=category,
            )

            specialist, routing_reasoning = self._parse_routing_response(raw_response)

            trace_entry = {
                "node": "route",
                "category": category,
                "question": question,
                "routed_to": specialist,
                "routing_reasoning": routing_reasoning,
                "expected_specialist": expected_specialist,
                "routing_correct": specialist == expected_specialist,
                "raw_routing_response": raw_response,
            }

            if specialist not in self.specialists:
                return {
                    "specialist_name": "",
                    "error": (
                        f"LLM routed to unknown specialist: {specialist!r}. "
                        f"Available: {list(self.specialists.keys())}"
                    ),
                    "trace": state.trace + [trace_entry],
                }

            return {
                "specialist_name": specialist,
                "trace": state.trace + [trace_entry],
            }

        except Exception as e:
            trace_entry = {
                "node": "route",
                "category": category,
                "error": str(e),
                "expected_specialist": expected_specialist,
            }
            return {
                "specialist_name": "",
                "error": f"Routing failed: {e}",
                "trace": state.trace + [trace_entry],
            }

    @staticmethod
    def _parse_routing_response(raw: str) -> tuple[str, str]:
        """Extract specialist name and reasoning from LLM routing response.

        Handles both clean JSON and JSON embedded in markdown/text.

        Returns:
            Tuple of (specialist_name, reasoning).
        """
        # Try direct JSON parse first
        try:
            data = json.loads(raw.strip())
            return data["specialist"], data.get("reasoning", "")
        except (json.JSONDecodeError, KeyError):
            pass

        # Fallback: extract JSON from surrounding text
        match = re.search(r'\{[^}]*"specialist"\s*:\s*"([^"]+)"[^}]*\}', raw)
        if match:
            # Try to also extract reasoning from the match
            reasoning_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', raw)
            reasoning = reasoning_match.group(1) if reasoning_match else ""
            return match.group(1), reasoning

        raise ValueError(f"Could not parse routing response: {raw!r}")

    def _get_specialist_route(self, state: GraphState) -> str:
        """Determine routing based on state.

        Args:
            state: Current graph state.

        Returns:
            Name of the next node to route to.
        """
        if state.error:
            return "error"
        return state.specialist_name

    def _make_specialist_node(self, specialist_name: str):
        """Create a node function for a specific specialist.

        Args:
            specialist_name: Name of the specialist agent.

        Returns:
            Node function for the specialist.
        """
        async def specialist_node(state: GraphState) -> dict[str, Any]:
            """Call the specialist agent for extraction.

            Args:
                state: Current graph state.

            Returns:
                Updated state with extraction_result.
            """
            specialist = self.specialists.get(specialist_name)

            trace_entry = {
                "node": specialist_name,
                "category": state.category,
            }

            if specialist is None:
                return {
                    "error": f"Specialist not found: {specialist_name}",
                    "trace": state.trace + [trace_entry],
                }

            try:
                result = await specialist.extract(
                    contract_text=state.contract_text,
                    category=state.category,
                    question=state.question,
                )
                trace_entry["extracted_count"] = len(result.extracted_clauses)
                trace_entry["confidence"] = result.confidence

                return {
                    "extraction_result": result,
                    "trace": state.trace + [trace_entry],
                }
            except Exception as e:
                trace_entry["error"] = str(e)
                return {
                    "error": f"Extraction failed: {e}",
                    "trace": state.trace + [trace_entry],
                }

        return specialist_node

    async def _validation_node(self, state: GraphState) -> dict[str, Any]:
        """Validate the extraction result.

        Args:
            state: Current graph state.

        Returns:
            Updated state with validation status.
        """
        trace_entry = {
            "node": "validate",
        }

        if state.extraction_result is None:
            return {
                "validated": False,
                "validation_notes": "No extraction result to validate",
                "trace": state.trace + [trace_entry],
            }

        if self.validation_agent is None:
            # Skip validation if no validation agent
            trace_entry["skipped"] = True
            return {
                "validated": True,
                "validation_notes": "Validation skipped (no validation agent)",
                "final_result": state.extraction_result,
                "trace": state.trace + [trace_entry],
            }

        try:
            validated_result = await self.validation_agent.verify(
                extraction_result=state.extraction_result,
                contract_text=state.contract_text,
                category=state.category,
            )
            trace_entry["grounding_checked"] = True

            return {
                "validated": True,
                "final_result": validated_result,
                "trace": state.trace + [trace_entry],
            }
        except Exception as e:
            trace_entry["error"] = str(e)
            # On validation error, use unvalidated result
            return {
                "validated": False,
                "validation_notes": f"Validation failed: {e}",
                "final_result": state.extraction_result,
                "trace": state.trace + [trace_entry],
            }

    def _finalize_node(self, state: GraphState) -> dict[str, Any]:
        """Finalize the extraction result.

        Args:
            state: Current graph state.

        Returns:
            Final state updates.
        """
        trace_entry = {
            "node": "finalize",
            "validated": state.validated,
            "has_error": state.error is not None,
        }

        if state.final_result is None and state.extraction_result is not None:
            return {
                "final_result": state.extraction_result,
                "trace": state.trace + [trace_entry],
            }

        return {
            "trace": state.trace + [trace_entry],
        }

    @staticmethod
    def get_expected_specialist(category: str) -> str:
        """Look up the ground-truth specialist for a category.

        Used for routing accuracy measurement, not for actual routing decisions.

        Args:
            category: The CUAD category.

        Returns:
            The expected specialist name.

        Raises:
            ValueError: If category is not recognized.
        """
        specialist = CATEGORY_ROUTING.get(category)
        if specialist is None:
            cat_lower = category.lower()
            for key, val in CATEGORY_ROUTING.items():
                if key.lower() == cat_lower:
                    specialist = val
                    break
        if specialist is None:
            raise ValueError(f"Unknown category: {category}")
        return specialist

    @observe(name="orchestrator.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> tuple[ExtractionResult, list[dict[str, Any]]]:
        """Run the full extraction workflow.

        Args:
            contract_text: The full contract text.
            category: The CUAD category to extract.
            question: The question prompt for this category.

        Returns:
            Tuple of (extraction_result, trace). Trace contains routing
            reasoning, accuracy, and node execution history.
        """
        # Initialize state
        initial_state = GraphState(
            contract_text=contract_text,
            category=category,
            question=question,
        )

        # Run the graph
        final_state = await self._compiled_graph.ainvoke(initial_state)

        trace = final_state.get("trace", [])

        # Extract result
        if final_state.get("error"):
            return ExtractionResult(
                extracted_clauses=[],
                reasoning=f"Error: {final_state['error']}",
                confidence=0.0,
                category=category,
            ), trace

        result = final_state.get("final_result")
        if result is None:
            return ExtractionResult(
                extracted_clauses=[],
                reasoning="No result produced",
                confidence=0.0,
                category=category,
            ), trace

        return result, trace

    def get_trace(self, state: GraphState) -> list[dict[str, Any]]:
        """Get the execution trace from a completed state.

        Args:
            state: Completed graph state.

        Returns:
            List of trace entries for explainability.
        """
        return state.trace
