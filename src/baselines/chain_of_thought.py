"""B4: Chain-of-Thought single-agent baseline."""

import logging
import re

from src.models.client import get_observe_decorator

observe = get_observe_decorator()

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult
from src.models import ModelDiagnostics

logger = logging.getLogger(__name__)


COT_SYSTEM_PROMPT = """You are an assistant with strong legal knowledge, supporting senior lawyers by preparing reference materials.

Given a Context and a Question, extract and return only the clause(s) or passage(s) from the Context that directly address or relate to the Question using step-by-step reasoning.

IMPORTANT:
- Extract clauses that directly address the Question. When uncertain whether a clause is relevant, include it — err on the side of inclusion rather than omission.
- Only respond "No related clause." if you have thoroughly searched the entire Context and found NOTHING relevant.
- Do NOT rephrase or summarize in any way — respond with exact text from the Context.
- If a relevant passage contains unrelated elements such as page numbers or whitespace, include them exactly as they appear.

Follow these steps in your reasoning:
1. What legal concept does the Question ask about?
2. Search the full Context for passages addressing this concept
3. For each candidate passage, does it directly answer the Question or is it only tangentially related?
4. Extract the complete passage — include surrounding text needed for the clause to make sense

After your reasoning, you MUST end your response with a line that says exactly:

Final Answer:

Followed by the extracted clause(s), each on its own line. If no relevant clause exists, write:

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

        # Safety net for missing or empty answer delimiter.
        #
        # Three cases:
        # 1. Delimiter found but nothing after it (e.g. "Final Answer:\n")
        #    → Treat as empty extraction (model declined to answer).
        # 2. No delimiter found in a long response (>500 chars)
        #    → Likely contains CoT reasoning that shouldn't become clauses.
        #      Use the last paragraph as a best-effort answer section.
        # 3. No delimiter found in a short response
        #    → Likely just the answer itself; use the full text.
        delimiter_found = any(
            re.search(p, text) for p in delimiter_patterns
        )
        if not answer_section:
            if delimiter_found:
                # Case 1: delimiter present but answer is empty/whitespace
                logger.debug(
                    "Answer delimiter found but answer section is empty. "
                    "Treating as empty extraction."
                )
                return ExtractionResult(
                    extracted_clauses=[],
                    reasoning=reasoning_section,
                    confidence=0.5,
                    category_indicators_found=[],
                )
            elif len(text) > 500:
                # Case 2: long response without delimiter — reasoning leaked
                paragraphs = [
                    p.strip() for p in text.split("\n\n") if p.strip()
                ]
                if len(paragraphs) > 1:
                    answer_section = paragraphs[-1]
                    reasoning_section = "\n\n".join(paragraphs[:-1])
                else:
                    answer_section = text
                logger.warning(
                    "No answer delimiter found in CoT response (%d chars). "
                    "Using last paragraph as answer section.",
                    len(text),
                )
            else:
                # Case 3: short response, probably just the answer
                answer_section = text

        # Detect negative responses: the model says "no clause" in various ways,
        # sometimes followed by lengthy commentary that shouldn't be parsed as
        # extracted clauses.
        if self._is_negative_response(answer_section):
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
            # Skip preamble/commentary lines (very short, no quotes, looks like intro)
            if re.match(r"(?i)^(the |these |here |a lawyer |relevant |extracted )", stripped) and len(stripped) < 60 and '"' not in stripped:
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

    # ------------------------------------------------------------------
    # Negative-response detection
    # ------------------------------------------------------------------

    # Patterns that indicate the first line is a negative statement
    _NEGATIVE_OPENER_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r'^"?\s*no\s+related\s+clause\b', re.IGNORECASE),
        re.compile(r"^no\s+explicit\b", re.IGNORECASE),
        re.compile(r"^no\s+clause\b", re.IGNORECASE),
        re.compile(r"^no\s+specific\s+(?:clause|provision)", re.IGNORECASE),
        re.compile(r"^the\s+(?:contract|agreement)\s+does\s+not\b", re.IGNORECASE),
        re.compile(r"^there\s+is\s+no\b", re.IGNORECASE),
    ]

    # Quoted-text patterns: actual contract extractions are typically >40
    # characters and enclosed in quotes (regular or smart).
    _QUOTED_TEXT_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r'"[^"]{40,}"'),
        re.compile(r"\u201c[^\u201d]{40,}\u201d"),  # smart double quotes
        re.compile(r"'[^']{40,}'"),
        re.compile(r"\u2018[^\u2019]{40,}\u2019"),  # smart single quotes
    ]

    def _is_negative_response(self, answer_section: str) -> bool:
        """Detect whether the answer section is a negative response.

        The model sometimes says "no clause found" in verbose ways —
        e.g. "No explicit X clause. However, the following sections..."
        — producing paragraphs of commentary that the clause parser
        would otherwise treat as extracted clauses.

        Detection strategy:
        1. Check if the first line matches a known negative-opener
           pattern (broadened beyond just "No related clause").
        2. If it does, look for actual quoted contract text (>40 chars).
           When the model says "no clause" but then quotes contract
           passages, those may be tangential extractions that the
           evaluator should score — so we let them through.
        3. If there are no quoted extractions, the answer is pure
           commentary and we treat it as a true negative.

        Args:
            answer_section: The text after the answer delimiter.

        Returns:
            True if the answer should be treated as "no clause found".
        """
        first_line = answer_section.split("\n")[0].strip()

        is_negative = any(
            p.match(first_line) for p in self._NEGATIVE_OPENER_PATTERNS
        )

        # Fallback: "No related clause" anywhere (not just first line)
        if not is_negative:
            is_negative = bool(
                re.search(
                    r'(?i)"?\s*no\s+related\s+clause\.?\s*"?', answer_section
                )
            )

        if not is_negative:
            return False

        # Negative opener detected. Only return True (empty extraction)
        # if there are no substantial quoted contract passages.
        has_quoted_extraction = any(
            p.search(answer_section) for p in self._QUOTED_TEXT_PATTERNS
        )

        if has_quoted_extraction:
            logger.debug(
                "Negative opener detected but answer contains quoted "
                "text (>40 chars). Letting extractions through."
            )
            return False

        return True
