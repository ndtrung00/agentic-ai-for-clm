"""B4: Chain-of-Thought single-agent baseline."""

from langfuse import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult
from src.models import ModelDiagnostics


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

    def __init__(
        self,
        config: AgentConfig | None = None,
        diagnostics: ModelDiagnostics | None = None,
    ) -> None:
        """Initialize the CoT baseline.

        Args:
            config: Optional agent configuration.
            diagnostics: Optional diagnostics collector.
        """
        if config is None:
            config = AgentConfig(name="cot_baseline")
        super().__init__(config, diagnostics)

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

        The full CoT prompt (with Context and Question) is sent as the user
        message.  The model's reasoning trace is preserved in the result.

        Args:
            contract_text: The full contract text.
            category: The CUAD category.
            question: The CUAD question.

        Returns:
            ExtractionResult with extracted clauses and reasoning.
        """
        user_message = COT_PROMPT.format(
            contract_text=contract_text,
            question=question,
        )
        messages = [{"role": "user", "content": user_message}]

        response = await self.invoke_model(
            messages=messages,
            category=category,
        )

        result = self.parse_response(response)
        result.category = category
        return result

    def parse_response(self, response: str) -> ExtractionResult:
        """Parse the CoT response into ExtractionResult.

        Splits reasoning from final answer.  Looks for common delimiters like
        "Final Answer:", "Extracted clauses:", "Answer:", or a trailing
        quoted block.  If no delimiter is found the full response is treated
        as the answer (same as zero-shot fallback).

        Args:
            response: Raw LLM response with reasoning.

        Returns:
            Parsed ExtractionResult.
        """
        import re

        text = response.strip()

        # Try to split on common answer delimiters
        answer_section = ""
        reasoning_section = text
        for marker in [
            r"(?i)final\s*answer\s*:",
            r"(?i)extracted\s*clauses?\s*:",
            r"(?i)answer\s*:",
            r"(?i)relevant\s*clauses?\s*:",
        ]:
            match = re.search(marker, text)
            if match:
                reasoning_section = text[: match.start()].strip()
                answer_section = text[match.end() :].strip()
                break

        # If no delimiter found, use the full text as the answer
        if not answer_section:
            answer_section = text

        # Check for "No related clause"
        if re.match(r'(?i)^"?no related clause\.?"?$', answer_section.strip()):
            return ExtractionResult(
                extracted_clauses=[],
                reasoning=reasoning_section,
                confidence=1.0,
                category_indicators_found=[],
            )

        # Split answer into individual clauses
        clauses = [c.strip() for c in answer_section.split("\n\n") if c.strip()]
        # Also handle numbered lists (e.g. "1. ...")
        if len(clauses) == 1:
            parts = re.split(r'\n\d+[\.\)]\s*', clauses[0])
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) > 1:
                clauses = parts

        # Strip surrounding quotes from each clause
        clauses = [c.strip('"').strip("'").strip() for c in clauses]
        clauses = [c for c in clauses if c]

        return ExtractionResult(
            extracted_clauses=clauses,
            reasoning=reasoning_section,
            confidence=0.8,
            category_indicators_found=[],
        )
