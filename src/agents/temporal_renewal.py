"""Temporal/Renewal specialist agent (11 categories)."""

from langfuse.decorators import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult


# Categories handled by this specialist
TEMPORAL_RENEWAL_CATEGORIES = [
    "Document Name",
    "Parties",
    "Agreement Date",
    "Effective Date",
    "Expiration Date",
    "Renewal Term",
    "Notice Period to Terminate Renewal",
    "Termination for Convenience",
    "Anti-Assignment",
    "Rofr/Rofo/Rofn",
    "Governing Law",
]


class TemporalRenewalAgent(BaseAgent):
    """Specialist agent for temporal and renewal clause extraction."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize the Temporal/Renewal specialist.

        Args:
            config: Optional agent configuration.
        """
        if config is None:
            config = AgentConfig(
                name="temporal_renewal",
                categories=TEMPORAL_RENEWAL_CATEGORIES,
            )
        super().__init__(config)

    def get_prompt(self, category: str) -> str:
        """Get the prompt template for a temporal/renewal category.

        Args:
            category: The CUAD category.

        Returns:
            The prompt template string.
        """
        # TODO: Load from YAML config
        base_prompt = """You are a legal expert specializing in temporal provisions, renewal terms, and contract administration clauses.

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
            "Document Name": [
                "agreement",
                "contract",
                "amendment",
                "addendum",
                "license agreement",
            ],
            "Parties": [
                "between",
                "party",
                "hereinafter",
                "undersigned",
                "contracting parties",
            ],
            "Agreement Date": [
                "dated",
                "as of",
                "entered into",
                "executed on",
            ],
            "Effective Date": [
                "effective date",
                "commencement date",
                "shall become effective",
                "takes effect",
            ],
            "Expiration Date": [
                "expiration",
                "termination date",
                "expires on",
                "shall terminate",
                "end date",
            ],
            "Renewal Term": [
                "renewal",
                "automatically renew",
                "successive terms",
                "extended",
                "renewal period",
            ],
            "Notice Period to Terminate Renewal": [
                "notice period",
                "days notice",
                "written notice",
                "prior to expiration",
            ],
            "Termination for Convenience": [
                "terminate for convenience",
                "terminate without cause",
                "at will",
                "discretion",
            ],
            "Anti-Assignment": [
                "assignment",
                "shall not assign",
                "non-assignable",
                "transfer of rights",
            ],
            "Rofr/Rofo/Rofn": [
                "right of first refusal",
                "right of first offer",
                "right of first negotiation",
                "ROFR",
                "ROFO",
            ],
            "Governing Law": [
                "governing law",
                "governed by",
                "laws of",
                "jurisdiction",
                "applicable law",
            ],
        }
        category_indicators = indicators.get(category, [])
        return "\n".join(f"- {ind}" for ind in category_indicators)

    @observe(name="temporal_renewal.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Extract temporal/renewal clauses from contract.

        Args:
            contract_text: The full contract text.
            category: The CUAD category to extract.
            question: The question prompt.

        Returns:
            ExtractionResult with extracted clauses.
        """
        # TODO: Implement LLM call with structured output
        raise NotImplementedError("LLM extraction not yet implemented")
