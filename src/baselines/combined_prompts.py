"""M6: Combined prompts single-agent baseline (critical ablation).

This baseline tests whether multi-agent benefits come from architecture
or just from the specialized prompts. It uses all the specialist knowledge
combined into a single agent with the SAME output format as B4 (plain text
with "Final Answer:" delimiter) for fair comparison.

KEY HYPOTHESIS: If M1 ≈ M6, multi-agent overhead is not justified.
If M1 > M6, architecture provides genuine benefit beyond prompting.
"""

import yaml
from pathlib import Path

from langfuse import observe

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult
from src.baselines.chain_of_thought import ChainOfThoughtBaseline
from src.models import ModelDiagnostics
from src.agents.orchestrator import CATEGORY_ROUTING


# ---------------------------------------------------------------------------
# Load category indicators from specialist YAML files
# ---------------------------------------------------------------------------

_SPECIALIST_DIR = Path(__file__).resolve().parent.parent.parent / "prompts" / "specialists"

_CATEGORY_INDICATORS: dict[str, list[str]] = {}
_DOMAIN_GUIDANCE: dict[str, dict[str, str]] = {}

for _yaml_file in _SPECIALIST_DIR.glob("*.yaml"):
    with open(_yaml_file) as _f:
        _data = yaml.safe_load(_f)
    _domain = _yaml_file.stem  # risk_liability, temporal_renewal, ip_commercial
    _DOMAIN_GUIDANCE[_domain] = {
        "system": _data.get("system", ""),
        "description": _data.get("description", ""),
    }
    for cat, indicators in (_data.get("category_indicators") or {}).items():
        _CATEGORY_INDICATORS[cat] = indicators


def _get_indicators(category: str) -> str:
    """Format indicators as a bullet list for a category."""
    indicators = _CATEGORY_INDICATORS.get(category, [])
    if not indicators:
        return "No specific indicators defined."
    return "\n".join(f"- {ind}" for ind in indicators)


def _get_domain(category: str) -> str:
    """Get the domain name for a category."""
    return CATEGORY_ROUTING.get(category, "unknown")


# ---------------------------------------------------------------------------
# Domain-specific guidance blocks (mirrors what M1 specialists know)
# ---------------------------------------------------------------------------

_DOMAIN_EXPERTISE = {
    "risk_liability": """RISK AND LIABILITY expertise:
- Liability limitations, caps, and uncapped liability
- Insurance and indemnification requirements
- Warranty provisions and durations
- Audit rights and compliance mechanisms
- Third-party considerations and beneficiaries
- Change of control provisions
- Consider negations (e.g., "shall not be liable" vs "shall be liable")""",

    "temporal_renewal": """TEMPORAL PROVISIONS AND RENEWAL expertise:
- Contract identification and party definitions
- Key dates (agreement, effective, expiration)
- Renewal and extension mechanisms
- Termination rights and notice periods
- Assignment restrictions
- Governing law and jurisdiction
- Pay attention to date formats and time periods
- Look for automatic renewal and opt-out provisions""",

    "ip_commercial": """INTELLECTUAL PROPERTY AND COMMERCIAL expertise:
- IP ownership, assignment, and joint ownership
- License grants and restrictions
- Exclusivity and non-compete provisions
- Non-solicitation agreements
- Commercial terms (pricing, volume, revenue sharing)
- License transferability and affiliate rights
- Distinguish between licensor and licensee provisions
- Look for scope limitations and geographic restrictions""",
}


# ---------------------------------------------------------------------------
# System prompt — combines all specialist knowledge with B4-style output
# ---------------------------------------------------------------------------

M6_SYSTEM_PROMPT = """You are an expert legal analyst with deep expertise in ALL areas of commercial contracts:

1. RISK AND LIABILITY: Liability caps, uncapped liability, insurance, warranties, indemnification, audit rights, third-party beneficiaries, change of control, post-termination services, minimum commitments.

2. TEMPORAL AND RENEWAL: Agreement dates, effective dates, expiration, renewal terms, notice periods, termination rights, assignment restrictions, rights of first refusal, governing law.

3. IP AND COMMERCIAL: IP ownership, license grants, exclusivity, non-compete provisions, non-solicitation, revenue sharing, pricing restrictions, volume limits, source code escrow, affiliate licensing.

Given a Context and a Question, extract and return only the sentence(s) from the Context that directly address or relate to the Question using step-by-step reasoning.

IMPORTANT:
- If you are uncertain whether a clause is relevant, INCLUDE IT.
- Only respond "No related clause." if you have thoroughly searched and found NOTHING relevant.
- Do NOT extract tangentially related sentences. Only extract sentences that directly address the Question.
- Do NOT rephrase or summarize — respond with exact sentences from the Context.

Follow these steps in your reasoning:
1. Identify the key legal concepts in the Question
2. Use the domain-specific indicators provided to guide your search
3. Scan the Context for sentences containing these concepts
4. For each potential match, evaluate if it DIRECTLY addresses the Question
5. Extract the exact text of relevant sentences

After your reasoning, you MUST end your response with a line that says exactly:

Final Answer:

Followed by the extracted sentence(s), each on its own line. If no relevant clause exists, write:

Final Answer:
No related clause."""


# ---------------------------------------------------------------------------
# User message template
# ---------------------------------------------------------------------------

M6_USER_TEMPLATE = """DOMAIN GUIDANCE ({domain}):
{domain_expertise}

CATEGORY-SPECIFIC INDICATORS for "{category}":
{indicators}

Context:
{contract_text}

Question:
{question}

Let's think step by step:"""


# ---------------------------------------------------------------------------
# Baseline class
# ---------------------------------------------------------------------------

class CombinedPromptsBaseline(BaseAgent):
    """M6: Single agent with combined specialist knowledge.

    Uses the same domain knowledge as M1's three specialists but in a
    single prompt. Output format matches B4 (plain text with "Final Answer:"
    delimiter) for fair comparison. Reuses B4's robust parser.
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        diagnostics: ModelDiagnostics | None = None,
    ) -> None:
        all_categories = list(CATEGORY_ROUTING.keys())
        if config is None:
            config = AgentConfig(
                name="combined_prompts",
                categories=all_categories,
            )
        super().__init__(config, diagnostics)
        self._cot_parser = ChainOfThoughtBaseline()

    def get_prompt(self, category: str) -> str:
        return M6_SYSTEM_PROMPT

    def get_domain_for_category(self, category: str) -> str:
        return _get_domain(category)

    @observe(name="combined_prompts.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Extract clauses using combined specialist prompting.

        System prompt provides combined expertise. User message includes
        domain-specific guidance and category indicators. Output uses
        "Final Answer:" delimiter, parsed by B4's robust parser.
        """
        domain = _get_domain(category)
        domain_expertise = _DOMAIN_EXPERTISE.get(domain, "General contract analysis.")

        user_message = M6_USER_TEMPLATE.format(
            domain=domain.replace("_", " ").title(),
            domain_expertise=domain_expertise,
            category=category,
            indicators=_get_indicators(category),
            contract_text=contract_text,
            question=question,
        )
        messages = [{"role": "user", "content": user_message}]

        response = await self.invoke_model(
            messages=messages,
            system=M6_SYSTEM_PROMPT,
            category=category,
        )

        result = self._cot_parser.parse_response(response)
        result.category = category
        return result
