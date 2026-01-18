"""B4: Chain-of-Thought single-agent baseline."""

from langfuse import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult


COT_PROMPT = """You are an assistant with strong legal knowledge, supporting senior lawyers by preparing reference materials.

Given a Context and a Question, you will extract relevant clauses using step-by-step reasoning.

IMPORTANT: If you are uncertain whether a clause is relevant, INCLUDE IT.
It is better to extract a potentially relevant clause than to miss one.
Only respond "No related clause" if you have thoroughly searched and found nothing.

Follow these steps:
1. First, identify the key concepts in the Question
2. Scan the Context for sentences containing these concepts
3. For each potential match, evaluate if it directly addresses the Question
4. Extract the exact text of relevant sentences (do not rephrase)
5. Provide your final answer

Context:
{contract_text}

Question:
{question}

Let's think step by step:
"""


class ChainOfThoughtBaseline(BaseAgent):
    """B4: Chain-of-Thought baseline with step-by-step reasoning."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize the CoT baseline.

        Args:
            config: Optional agent configuration.
        """
        if config is None:
            config = AgentConfig(name="cot_baseline")
        super().__init__(config)

    def get_prompt(self, category: str) -> str:
        """Get the Chain-of-Thought prompt template.

        Args:
            category: The CUAD category.

        Returns:
            The CoT prompt template.
        """
        return COT_PROMPT

    @observe(name="chain_of_thought.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Extract clauses using chain-of-thought prompting.

        Args:
            contract_text: The full contract text.
            category: The CUAD category.
            question: The CUAD question.

        Returns:
            ExtractionResult with extracted clauses and reasoning.
        """
        # TODO: Implement LLM call with CoT
        raise NotImplementedError("LLM extraction not yet implemented")

    def parse_response(self, response: str) -> ExtractionResult:
        """Parse the CoT response into ExtractionResult.

        Args:
            response: Raw LLM response with reasoning.

        Returns:
            Parsed ExtractionResult.
        """
        # TODO: Parse reasoning and final answer from response
        # Look for patterns like "Final Answer:" or "Extracted clauses:"
        raise NotImplementedError("Response parsing not yet implemented")
