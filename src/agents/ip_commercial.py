"""IP & Commercial specialist agent (17 categories)."""

from langfuse.decorators import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult


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

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize the IP & Commercial specialist.

        Args:
            config: Optional agent configuration.
        """
        if config is None:
            config = AgentConfig(
                name="ip_commercial",
                categories=IP_COMMERCIAL_CATEGORIES,
            )
        super().__init__(config)

    def get_prompt(self, category: str) -> str:
        """Get the prompt template for an IP/commercial category.

        Args:
            category: The CUAD category.

        Returns:
            The prompt template string.
        """
        # TODO: Load from YAML config
        base_prompt = """You are a legal expert specializing in intellectual property, licensing, and commercial terms in contracts.

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
            "Ip Ownership Assignment": [
                "assigns",
                "transfer of ownership",
                "work for hire",
                "intellectual property rights",
                "all rights",
            ],
            "Joint Ip Ownership": [
                "joint ownership",
                "jointly own",
                "shared ownership",
                "co-owned",
            ],
            "License Grant": [
                "hereby grants",
                "license to use",
                "right to use",
                "licensed",
                "permission",
            ],
            "Non-Transferable License": [
                "non-transferable",
                "not transferable",
                "personal license",
                "may not transfer",
            ],
            "Exclusivity": [
                "exclusive",
                "sole",
                "exclusively",
                "only provider",
            ],
            "Non-Compete": [
                "non-compete",
                "not compete",
                "competitive activity",
                "restriction on competition",
            ],
            "No-Solicit Of Customers": [
                "non-solicitation",
                "not solicit customers",
                "customer relationships",
            ],
            "No-Solicit Of Employees": [
                "non-solicitation",
                "not solicit employees",
                "not hire employees",
                "personnel",
            ],
            "Revenue/Profit Sharing": [
                "revenue sharing",
                "profit sharing",
                "royalty",
                "percentage of revenue",
            ],
            "Price Restrictions": [
                "price",
                "pricing",
                "minimum price",
                "resale price",
                "price maintenance",
            ],
            "Volume Restriction": [
                "volume",
                "quantity",
                "minimum order",
                "maximum",
                "units",
            ],
            # TODO: Add indicators for remaining categories
        }
        category_indicators = indicators.get(category, [])
        return "\n".join(f"- {ind}" for ind in category_indicators)

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
        # TODO: Implement LLM call with structured output
        raise NotImplementedError("LLM extraction not yet implemented")
