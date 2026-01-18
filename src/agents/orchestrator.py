"""Orchestrator agent that routes queries to specialist agents."""

from typing import TYPE_CHECKING

from langfuse.decorators import observe
from langgraph.graph import StateGraph, END

from src.agents.base import AgentConfig, ExtractionResult

if TYPE_CHECKING:
    from src.agents.base import BaseAgent


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


class Orchestrator:
    """Routes extraction queries to appropriate specialist agents."""

    def __init__(
        self,
        specialists: dict[str, "BaseAgent"],
        validation_agent: "BaseAgent | None" = None,
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

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow.

        Returns:
            Configured StateGraph for the multi-agent workflow.
        """
        # TODO: Implement LangGraph workflow
        # This will define the routing logic and agent handoffs
        raise NotImplementedError("LangGraph workflow not yet implemented")

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
        """Route extraction to appropriate specialist and validate.

        Args:
            contract_text: The full contract text.
            category: The CUAD category to extract.
            question: The question prompt for this category.

        Returns:
            Validated extraction result.
        """
        # Route to specialist
        specialist_name = self.route_category(category)
        specialist = self.specialists.get(specialist_name)

        if specialist is None:
            raise ValueError(f"Specialist not found: {specialist_name}")

        # Get extraction from specialist
        result = await specialist.extract(contract_text, category, question)

        # Optionally validate
        if self.validation_agent is not None:
            result = await self._validate_result(result, contract_text)

        return result

    async def _validate_result(
        self,
        result: ExtractionResult,
        contract_text: str,
    ) -> ExtractionResult:
        """Validate extraction result using validation agent.

        Args:
            result: The extraction result to validate.
            contract_text: Original contract text for grounding check.

        Returns:
            Validated (potentially corrected) extraction result.
        """
        if self.validation_agent is None:
            return result

        # TODO: Implement validation logic
        return result
