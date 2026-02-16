"""B1: Zero-shot single-agent baseline (ContractEval replication)."""

from langfuse import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult
from src.models import ModelDiagnostics


# ContractEval exact prompt - MUST REPLICATE EXACTLY
CONTRACTEVAL_PROMPT = """You are an assistant with strong legal knowledge, supporting senior lawyers by preparing reference materials. Given a Context and a Question, extract and return only the sentence(s) from the Context that directly address or relate to the Question. Do not rephrase or summarize in any way—respond with exact sentences from the Context relevant to the Question. If a relevant sentence contains unrelated elements such as page numbers or whitespace, include them exactly as they appear. If no part of the Context is relevant to the Question, respond with: "No related clause."
"""


class ZeroShotBaseline(BaseAgent):
    """B1: Zero-shot baseline replicating ContractEval methodology."""

    def __init__(
        self,
        config: AgentConfig | None = None,
        diagnostics: ModelDiagnostics | None = None,
    ) -> None:
        """Initialize the zero-shot baseline.

        Args:
            config: Optional agent configuration.
            diagnostics: Optional diagnostics collector.
        """
        if config is None:
            config = AgentConfig(name="zero_shot_baseline")
        super().__init__(config, diagnostics)

    def get_prompt(self, category: str) -> str:
        """Get the ContractEval prompt template.

        Args:
            category: The CUAD category (not used in zero-shot).

        Returns:
            The ContractEval prompt.
        """
        return CONTRACTEVAL_PROMPT

    def format_input(self, contract_text: str, question: str) -> str:
        """Format input for the ContractEval prompt.

        Args:
            contract_text: The contract text.
            question: The CUAD question for this category.

        Returns:
            Formatted input string.
        """
        return f"""Context:
{contract_text}

Question:
{question}"""

    @observe(name="zero_shot.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Extract clauses using zero-shot prompting.

        Replicates ContractEval methodology exactly: system prompt sets the
        role, user message provides Context + Question.

        Args:
            contract_text: The full contract text.
            category: The CUAD category.
            question: The CUAD question.

        Returns:
            ExtractionResult with extracted clauses.
        """
        user_message = self.format_input(contract_text, question)
        messages = [{"role": "user", "content": user_message}]

        response = await self.invoke_model(
            messages=messages,
            system=CONTRACTEVAL_PROMPT,
            category=category,
        )

        result = self.parse_response(response)
        result.category = category
        return result

    def parse_response(self, response: str) -> ExtractionResult:
        """Parse the raw LLM response into ExtractionResult.

        Args:
            response: Raw LLM response text.

        Returns:
            Parsed ExtractionResult.
        """
        # Handle "No related clause" response
        if response.strip().lower() == "no related clause.":
            return ExtractionResult(
                extracted_clauses=[],
                reasoning="Model found no relevant clauses",
                confidence=1.0,
                category_indicators_found=[],
            )

        # Otherwise, the response should be the extracted clause(s)
        # Split on common delimiters if multiple clauses
        clauses = [c.strip() for c in response.split("\n\n") if c.strip()]

        return ExtractionResult(
            extracted_clauses=clauses,
            reasoning="Zero-shot extraction",
            confidence=0.8,  # Default confidence for zero-shot
            category_indicators_found=[],
        )
