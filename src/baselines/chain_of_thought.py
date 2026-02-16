"""B4: Chain-of-Thought single-agent baseline."""

import re

from langfuse import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult
from src.models import ModelDiagnostics


COT_SYSTEM_PROMPT = """You are an assistant with strong legal knowledge, supporting senior lawyers by preparing reference materials.

Given a Context and a Question, extract and return only the sentence(s) from the Context that directly address or relate to the Question using step-by-step reasoning.

IMPORTANT:
- If you are uncertain whether a clause is relevant, INCLUDE IT.
- Only respond "No related clause." if you have thoroughly searched and found NOTHING relevant.
- Do NOT extract tangentially related sentences. Only extract sentences that directly address the Question.
- Do NOT rephrase or summarize — respond with exact sentences from the Context.

Follow these steps in your reasoning:
1. Identify the key legal concepts in the Question
2. Scan the Context for sentences containing these concepts
3. For each potential match, evaluate if it DIRECTLY addresses the Question
4. Extract the exact text of relevant sentences

After your reasoning, you MUST end your response with a line that says exactly:

Final Answer:

Followed by the extracted sentence(s), each on its own line. If no relevant clause exists, write:

Final Answer:
No related clause."""


COT_USER_TEMPLATE = """Context:
{contract_text}

Question:
{question}

Let's think step by step:"""


# Keep the old prompt available for reference / summary JSON
COT_PROMPT = COT_SYSTEM_PROMPT


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
        """Get the Chain-of-Thought system prompt.

        Args:
            category: The CUAD category.

        Returns:
            The CoT system prompt.
        """
        return COT_SYSTEM_PROMPT

    @observe(name="chain_of_thought.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Extract clauses using chain-of-thought prompting.

        System prompt provides CoT instructions. User message provides
        the contract context and question. The model's reasoning trace
        is preserved in the result.

        Args:
            contract_text: The full contract text.
            category: The CUAD category.
            question: The CUAD question.

        Returns:
            ExtractionResult with extracted clauses and reasoning.
        """
        user_message = COT_USER_TEMPLATE.format(
            contract_text=contract_text,
            question=question,
        )
        messages = [{"role": "user", "content": user_message}]

        response = await self.invoke_model(
            messages=messages,
            system=COT_SYSTEM_PROMPT,
            category=category,
        )

        result = self.parse_response(response)
        result.category = category
        return result

    def parse_response(self, response: str) -> ExtractionResult:
        """Parse the CoT response into ExtractionResult.

        Splits reasoning from final answer using flexible delimiter
        detection. Handles variations like "Final Answer:", "Step 5:
        Final answer", "Final answer\n", etc.

        Args:
            response: Raw LLM response with reasoning.

        Returns:
            Parsed ExtractionResult.
        """
        text = response.strip()

        # Try to split on answer delimiters (ordered by specificity)
        answer_section = ""
        reasoning_section = text
        delimiter_patterns = [
            # "Final Answer:" or "Final answer:" (with trailing colon)
            r"(?i)final\s*answer\s*:",
            # "Step N: Final answer" (no trailing colon, common with CoT)
            r"(?i)step\s*\d+\s*[.:]\s*final\s*answer\s*",
            # "Extracted clause(s):"
            r"(?i)extracted\s*clauses?\s*:",
            # "Relevant clause(s):"
            r"(?i)relevant\s*clauses?\s*:",
            # "Answer:" (generic, last resort)
            r"(?i)(?:^|\n)\s*answer\s*:",
        ]

        for pattern in delimiter_patterns:
            match = re.search(pattern, text)
            if match:
                reasoning_section = text[: match.start()].strip()
                answer_section = text[match.end() :].strip()
                break

        # If no delimiter found, use the full text as the answer
        if not answer_section:
            answer_section = text

        # Check for "No related clause" anywhere in the answer section
        no_clause_pattern = r'(?i)"?\s*no\s+related\s+clause\.?\s*"?'
        if re.search(no_clause_pattern, answer_section):
            # Only treat as "no clause" if there are no actual extractions after it
            # Remove the "no related clause" line and check if anything substantive remains
            cleaned = re.sub(no_clause_pattern, "", answer_section).strip()
            # Filter out commentary lines (lines without quotes or contract-like text)
            remaining_lines = [
                line.strip() for line in cleaned.split("\n")
                if line.strip()
                and not line.strip().startswith("(")
                and len(line.strip()) > 20
            ]
            if not remaining_lines:
                return ExtractionResult(
                    extracted_clauses=[],
                    reasoning=reasoning_section,
                    confidence=1.0,
                    category_indicators_found=[],
                )

        # Clean the answer section: remove preamble lines like
        # "The relevant clauses are:" or "A lawyer should review:"
        lines = answer_section.split("\n")
        clause_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Skip preamble/commentary lines (short, no quotes, looks like intro)
            if re.match(r"(?i)^(the |these |here |a lawyer |relevant |extracted )", stripped) and len(stripped) < 120 and '"' not in stripped:
                continue
            clause_lines.append(stripped)

        # Rejoin and split into clauses on double newlines or bullet markers
        answer_text = "\n".join(clause_lines)

        # Split on bullet/dash markers
        clauses = re.split(r"\n\s*[-•]\s+", answer_text)
        # If no bullets, split on double newlines
        if len(clauses) <= 1:
            clauses = [c.strip() for c in answer_text.split("\n\n") if c.strip()]
        # Handle numbered lists
        if len(clauses) == 1:
            parts = re.split(r"\n\d+[.)]\s*", clauses[0])
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) > 1:
                clauses = parts

        # Clean each clause: strip quotes, bullets, whitespace
        cleaned_clauses = []
        for c in clauses:
            c = c.strip().lstrip("-•").strip()
            c = c.strip('"').strip("'").strip()
            if c and len(c) > 5:
                cleaned_clauses.append(c)

        return ExtractionResult(
            extracted_clauses=cleaned_clauses,
            reasoning=reasoning_section,
            confidence=0.8,
            category_indicators_found=[],
        )
