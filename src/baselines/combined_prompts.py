"""M6: Combined prompts single-agent baseline (critical ablation).

This baseline tests whether multi-agent benefits come from architecture
or just from the specialized prompts. It uses all the specialist prompts
combined into a single agent.

KEY HYPOTHESIS: If M1 ≈ M6, multi-agent overhead is not justified.
If M1 > M6, architecture provides genuine benefit beyond prompting.
"""

from langfuse import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult
from src.models import ModelDiagnostics
from src.agents.risk_liability import RISK_LIABILITY_CATEGORIES
from src.agents.temporal_renewal import TEMPORAL_RENEWAL_CATEGORIES
from src.agents.ip_commercial import IP_COMMERCIAL_CATEGORIES


COMBINED_PROMPT = """You are an expert legal analyst with deep expertise in:
1. Risk and Liability clauses (caps, insurance, warranties, indemnification)
2. Temporal and Renewal provisions (dates, terms, termination, assignment)
3. IP and Commercial terms (licensing, ownership, restrictions, competition)

Your task is to extract clauses related to: {category}

DOMAIN-SPECIFIC GUIDANCE:

FOR RISK & LIABILITY CATEGORIES:
Look for: liability caps, uncapped liability, liquidated damages, insurance requirements,
warranty periods, audit rights, indemnification, most favored nation clauses.

FOR TEMPORAL & RENEWAL CATEGORIES:
Look for: agreement dates, effective dates, expiration, renewal terms, notice periods,
termination rights, assignment restrictions, governing law provisions.

FOR IP & COMMERCIAL CATEGORIES:
Look for: IP ownership, license grants, exclusivity, non-compete provisions,
solicitation restrictions, revenue sharing, price/volume restrictions.

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


class CombinedPromptsBaseline(BaseAgent):
    """M6: Single agent with combined specialist knowledge.

    This is a critical ablation to test if multi-agent benefits
    come from architecture or just from specialized prompting.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        diagnostics: ModelDiagnostics | None = None,
    ) -> None:
        """Initialize the combined prompts baseline.

        Args:
            config: Optional agent configuration.
            diagnostics: Optional diagnostics collector.
        """
        all_categories = (
            RISK_LIABILITY_CATEGORIES
            + TEMPORAL_RENEWAL_CATEGORIES
            + IP_COMMERCIAL_CATEGORIES
        )
        if config is None:
            config = AgentConfig(
                name="combined_prompts",
                categories=all_categories,
            )
        super().__init__(config, diagnostics)

    def get_prompt(self, category: str) -> str:
        """Get the combined prompt template.

        Args:
            category: The CUAD category.

        Returns:
            The combined prompt template.
        """
        return COMBINED_PROMPT

    def get_domain_for_category(self, category: str) -> str:
        """Determine which domain a category belongs to.

        Args:
            category: The CUAD category.

        Returns:
            Domain name for logging/analysis.
        """
        if category in RISK_LIABILITY_CATEGORIES:
            return "risk_liability"
        elif category in TEMPORAL_RENEWAL_CATEGORIES:
            return "temporal_renewal"
        elif category in IP_COMMERCIAL_CATEGORIES:
            return "ip_commercial"
        else:
            return "unknown"

    @observe(name="combined_prompts.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Extract clauses using combined specialist prompting.

        Sends the combined prompt (all domain guidance in one) as the user
        message and requests structured JSON output.

        Args:
            contract_text: The full contract text.
            category: The CUAD category.
            question: The CUAD question.

        Returns:
            ExtractionResult with extracted clauses.
        """
        user_message = COMBINED_PROMPT.format(
            category=category,
            contract_text=contract_text,
            question=question,
        )
        messages = [{"role": "user", "content": user_message}]

        response = await self.invoke_model(
            messages=messages,
            category=category,
        )

        # Try JSON parsing first; fall back to plain-text extraction
        data = self.parse_json_response(response)
        if data and "extracted_clauses" in data:
            result = self.result_from_dict(data, category)
        else:
            result = self._parse_plaintext(response, category)

        return result

    def _parse_plaintext(self, response: str, category: str) -> ExtractionResult:
        """Fallback parser when model doesn't return valid JSON.

        Args:
            response: Raw model response.
            category: The CUAD category.

        Returns:
            ExtractionResult parsed from plain text.
        """
        text = response.strip()

        if text.lower().strip('"').strip() in ("no related clause.", "no related clause"):
            return ExtractionResult(
                extracted_clauses=[],
                reasoning="Model found no relevant clauses",
                confidence=1.0,
                category=category,
            )

        clauses = [c.strip() for c in text.split("\n\n") if c.strip()]
        return ExtractionResult(
            extracted_clauses=clauses,
            reasoning="Combined prompts extraction (plaintext fallback)",
            confidence=0.7,
            category=category,
        )
