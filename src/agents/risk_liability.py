"""Risk & Liability specialist agent (13 categories)."""

from langfuse import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult
from src.models import ModelDiagnostics


# Categories handled by this specialist
RISK_LIABILITY_CATEGORIES = [
    "Uncapped Liability",
    "Cap on Liability",
    "Liquidated Damages",
    "Insurance",
    "Warranty Duration",
    "Audit Rights",
    "Non-Disparagement",
    "Covenant Not to Sue",
    "Third Party Beneficiary",
    "Most Favored Nation",
    "Change of Control",
    "Post-Termination Services",
    "Minimum Commitment",
]


class RiskLiabilityAgent(BaseAgent):
    """Specialist agent for risk and liability clause extraction."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        diagnostics: ModelDiagnostics | None = None,
    ) -> None:
        """Initialize the Risk & Liability specialist.

        Args:
            config: Optional agent configuration.
            diagnostics: Optional diagnostics collector.
        """
        if config is None:
            config = AgentConfig(
                name="risk_liability",
                prompt_name="risk_liability",
                categories=RISK_LIABILITY_CATEGORIES,
            )
        super().__init__(config, diagnostics)

    @observe(name="risk_liability.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Extract risk/liability clauses from contract.

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
