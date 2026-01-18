"""Orchestrator agent using LangGraph for workflow management."""

from typing import Any
from dataclasses import dataclass, field

from langfuse.decorators import observe
from langgraph.graph import StateGraph, END, START

from src.agents.base import AgentConfig, ExtractionResult


# Category to specialist mapping
CATEGORY_ROUTING: dict[str, str] = {
    # Risk & Liability (13 categories)
    "Uncapped Liability": "risk_liability",
    "Cap on Liability": "risk_liability",
    "Liquidated Damages": "risk_liability",
    "Insurance": "risk_liability",
    "Warranty Duration": "risk_liability",
    "Audit Rights": "risk_liability",
    "Non-Disparagement": "risk_liability",
    "Covenant Not to Sue": "risk_liability",
    "Third Party Beneficiary": "risk_liability",
    "Most Favored Nation": "risk_liability",
    "Change of Control": "risk_liability",
    "Post-Termination Services": "risk_liability",
    "Minimum Commitment": "risk_liability",
    # Temporal/Renewal (11 categories)
    "Document Name": "temporal_renewal",
    "Parties": "temporal_renewal",
    "Agreement Date": "temporal_renewal",
    "Effective Date": "temporal_renewal",
    "Expiration Date": "temporal_renewal",
    "Renewal Term": "temporal_renewal",
    "Notice Period to Terminate Renewal": "temporal_renewal",
    "Termination for Convenience": "temporal_renewal",
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
    1. START -> route_to_specialist (determine which specialist handles category)
    2. route_to_specialist -> specialist_node (call appropriate specialist)
    3. specialist_node -> validation_node (validate extraction)
    4. validation_node -> END (return final result)
    """

    def __init__(
        self,
        specialists: dict[str, Any],  # BaseAgent instances
        validation_agent: Any | None = None,  # ValidationAgent instance
        config: AgentConfig | None = None,
    ) -> None:
        """Initialize the orchestrator.

        Args:
            specialists: Dict mapping specialist names to agent instances.
            validation_agent: Optional validation agent for grounding checks.
            config: Optional orchestrator configuration.
        """
        self.specialists = specialists
        self.validation_agent = validation_agent
        self.config = config or AgentConfig(name="orchestrator")
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

    def _route_node(self, state: GraphState) -> dict[str, Any]:
        """Route to the appropriate specialist based on category.

        Args:
            state: Current graph state.

        Returns:
            Updated state with specialist_name set.
        """
        category = state.category
        specialist = CATEGORY_ROUTING.get(category)

        trace_entry = {
            "node": "route",
            "category": category,
            "routed_to": specialist,
        }

        if specialist is None:
            return {
                "specialist_name": "",
                "error": f"Unknown category: {category}",
                "trace": state.trace + [trace_entry],
            }

        return {
            "specialist_name": specialist,
            "trace": state.trace + [trace_entry],
        }

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

    def route_category(self, category: str) -> str:
        """Determine which specialist handles a category.

        Args:
            category: The CUAD category to route.

        Returns:
            The specialist name that handles this category.

        Raises:
            ValueError: If category is not recognized.
        """
        specialist = CATEGORY_ROUTING.get(category)
        if specialist is None:
            raise ValueError(f"Unknown category: {category}")
        return specialist

    @observe(name="orchestrator.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Run the full extraction workflow.

        Args:
            contract_text: The full contract text.
            category: The CUAD category to extract.
            question: The question prompt for this category.

        Returns:
            Final extraction result after specialist and validation.
        """
        # Initialize state
        initial_state = GraphState(
            contract_text=contract_text,
            category=category,
            question=question,
        )

        # Run the graph
        final_state = await self._compiled_graph.ainvoke(initial_state)

        # Extract result
        if final_state.get("error"):
            # Return empty result on error
            return ExtractionResult(
                extracted_clauses=[],
                reasoning=f"Error: {final_state['error']}",
                confidence=0.0,
                category=category,
            )

        result = final_state.get("final_result")
        if result is None:
            return ExtractionResult(
                extracted_clauses=[],
                reasoning="No result produced",
                confidence=0.0,
                category=category,
            )

        return result

    def get_trace(self, state: GraphState) -> list[dict[str, Any]]:
        """Get the execution trace from a completed state.

        Args:
            state: Completed graph state.

        Returns:
            List of trace entries for explainability.
        """
        return state.trace
