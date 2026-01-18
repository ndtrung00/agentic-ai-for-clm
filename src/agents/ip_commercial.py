"""IP & Commercial specialist agent (17 categories)."""

from langfuse import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult
from src.models import ModelDiagnostics


# Categories handled by this specialist
IP_COMMERCIAL_CATEGORIES = [
    "Ip Ownership Assignment",
    "Joint Ip Ownership",
    "License Grant",
    "Non-Transferable License",
    "Affiliate License-Licensor",
    "Affiliate License-Licensee",
    "Unlimited/All-You-Can-Eat-License",
    "Irrevocable Or Perpetual License",
    "Source Code Escrow",
    "Exclusivity",
    "Non-Compete",
    "No-Solicit Of Customers",
    "No-Solicit Of Employees",
    "Competitive Restriction Exception",
    "Revenue/Profit Sharing",
    "Price Restrictions",
    "Volume Restriction",
]


class IPCommercialAgent(BaseAgent):
    """Specialist agent for IP and commercial clause extraction."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        diagnostics: ModelDiagnostics | None = None,
    ) -> None:
        """Initialize the IP & Commercial specialist.

        Args:
            config: Optional agent configuration.
            diagnostics: Optional diagnostics collector.
        """
        if config is None:
            config = AgentConfig(
                name="ip_commercial",
                prompt_name="ip_commercial",
                categories=IP_COMMERCIAL_CATEGORIES,
            )
        super().__init__(config, diagnostics)

    @observe(name="ip_commercial.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Extract IP/commercial clauses from contract.

        Args:
            contract_text: The full contract text.
            category: The CUAD category to extract.
            question: The question prompt.

        Returns:
            ExtractionResult with extracted clauses.
        """
        # Get formatted prompts from template
        indicators = self.get_indicators(category)
        system_prompt, user_prompt = self.prompt_template.format(
            category=category,
            indicators=indicators,
            contract_text=contract_text,
            question=question,
        )

        # Call the model
        messages = [{"role": "user", "content": user_prompt}]
        response = await self.invoke_model(
            messages=messages,
            system=system_prompt,
            category=category,
        )

        # Parse response to ExtractionResult
        parsed = self.parse_json_response(response)

        if not parsed:
            # If JSON parsing failed, try to extract clauses from raw text
            return ExtractionResult(
                extracted_clauses=[response] if "No related clause" not in response else [],
                reasoning="Failed to parse JSON response",
                confidence=0.5,
                category=category,
            )

        return self.result_from_dict(parsed, category)
