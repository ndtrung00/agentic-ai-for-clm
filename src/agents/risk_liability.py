"""Risk & Liability specialist agent (13 categories)."""

from langfuse.decorators import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult


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

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize the Risk & Liability specialist.

        Args:
            config: Optional agent configuration.
        """
        if config is None:
            config = AgentConfig(
                name="risk_liability",
                categories=RISK_LIABILITY_CATEGORIES,
            )
        super().__init__(config)

    def get_prompt(self, category: str) -> str:
        """Get the prompt template for a risk/liability category.

        Args:
            category: The CUAD category.

        Returns:
            The prompt template string.
        """
        # TODO: Load from YAML config
        base_prompt = """You are a legal expert specializing in risk and liability clauses in commercial contracts.

Your task is to extract clauses related to: {category}

CATEGORY-SPECIFIC INDICATORS:
{indicators}

IMPORTANT: If you are uncertain whether a clause is relevant, INCLUDE IT.
It is better to extract a potentially relevant clause than to miss one.
Only respond "No related clause" if you have thoroughly searched and found nothing.

Given the following contract text, extract all relevant clauses exactly as they appear.

CONTRACT TEXT:
{contract_text}

QUESTION: {question}

Respond with a JSON object containing:
- extracted_clauses: list of exact text excerpts from the contract
- reasoning: step-by-step explanation of your extraction logic
- confidence: float between 0 and 1
- category_indicators_found: list of specific terms/patterns found
"""
        return base_prompt

    def _get_category_indicators(self, category: str) -> str:
        """Get category-specific indicators for the prompt.

        Args:
            category: The CUAD category.

        Returns:
            Formatted string of indicators to look for.
        """
        indicators: dict[str, list[str]] = {
            "Uncapped Liability": [
                "unlimited liability",
                "no cap",
                "without limitation",
                "full liability",
                "uncapped",
            ],
            "Cap on Liability": [
                "liability cap",
                "maximum liability",
                "not exceed",
                "limited to",
                "aggregate liability",
                "$X million",
            ],
            "Liquidated Damages": [
                "liquidated damages",
                "predetermined damages",
                "fixed damages",
                "agreed damages",
            ],
            "Insurance": [
                "insurance",
                "coverage",
                "policy",
                "indemnity insurance",
                "liability insurance",
            ],
            # TODO: Add indicators for remaining categories
        }
        category_indicators = indicators.get(category, [])
        return "\n".join(f"- {ind}" for ind in category_indicators)

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
        # TODO: Implement LLM call with structured output
        raise NotImplementedError("LLM extraction not yet implemented")
