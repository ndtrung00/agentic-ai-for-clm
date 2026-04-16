"""Validation agent for grounding and format verification."""

from src.models.client import get_observe_decorator

observe = get_observe_decorator()

from src.agents.base import AgentConfig, BaseAgent, ExtractionResult


class ValidationAgent(BaseAgent):
    """Agent that validates extraction results for grounding and format."""

    def __init__(self, config: AgentConfig | None = None) -> None:
        """Initialize the validation agent.

        Args:
            config: Optional agent configuration.
        """
        if config is None:
            config = AgentConfig(name="validation", categories=[])
        super().__init__(config)

    def get_prompt(self, category: str) -> str:
        """Get the validation prompt template.

        Args:
            category: The CUAD category (not used for validation).

        Returns:
            The validation prompt template.
        """
        return """You are a validation agent responsible for verifying contract clause extractions.

Your tasks:
1. GROUNDING CHECK: Verify each extracted clause appears verbatim in the contract
2. RELEVANCE CHECK: Confirm the clause actually relates to the category
3. LAZINESS CHECK: If result is "No related clause", double-check the contract

EXTRACTED RESULT:
{extraction_result}

ORIGINAL CONTRACT:
{contract_text}

CATEGORY: {category}

For each extracted clause, verify:
- Does this exact text appear in the contract? (grounding)
- Is this clause relevant to the category? (relevance)

If the result was "No related clause":
- Search again for any potentially relevant clauses
- List any clauses that might have been missed

Respond with a JSON object containing:
- validated_clauses: list of verified clauses
- removed_clauses: list of clauses that failed validation (with reasons)
- missed_clauses: list of clauses found during re-check
- grounding_rate: float (validated / total extracted)
- validation_notes: string explaining any issues found
"""

    @observe(name="validation.verify")
    async def verify(
        self,
        extraction_result: ExtractionResult,
        contract_text: str,
        category: str,
    ) -> ExtractionResult:
        """Verify an extraction result for grounding and relevance.

        Performs two checks without an LLM call:
        1. Grounding: each extracted clause must appear verbatim in the contract
        2. Reasoning contradiction: if the reasoning says "no clause found" but
           clauses were extracted, drop the clauses

        Args:
            extraction_result: The result to validate.
            contract_text: Original contract for grounding check.
            category: The CUAD category for relevance check.

        Returns:
            Validated (potentially corrected) ExtractionResult.
        """
        if not extraction_result.extracted_clauses:
            return extraction_result

        # Check 1: Reasoning contradiction — only drop when model strongly
        # says nothing exists (not when it's qualifying like "no specific X, but...")
        reasoning_lower = extraction_result.reasoning.lower()
        strong_negatives = [
            "no related clause",
            "no relevant clause",
            "no clause found",
            "found no relevant",
            "found nothing relevant",
            "nothing relevant",
        ]
        # Only trigger if a strong negative appears AND reasoning doesn't contain "but" / "however"
        # which indicates the model is qualifying, not contradicting
        has_strong_negative = any(phrase in reasoning_lower for phrase in strong_negatives)
        has_qualifier = any(q in reasoning_lower for q in [" but ", " however ", " although ", " nonetheless "])
        if has_strong_negative and not has_qualifier:
            return ExtractionResult(
                extracted_clauses=[],
                reasoning=f"Validation: reasoning contradicts extraction. Original reasoning: {extraction_result.reasoning}",
                confidence=extraction_result.confidence,
                category_indicators_found=extraction_result.category_indicators_found,
                category=extraction_result.category,
            )

        # Check 2: Grounding — keep only clauses that appear in the contract
        grounded = []
        for clause in extraction_result.extracted_clauses:
            if self.check_grounding(clause, contract_text):
                grounded.append(clause)

        return ExtractionResult(
            extracted_clauses=grounded,
            reasoning=extraction_result.reasoning,
            confidence=extraction_result.confidence,
            category_indicators_found=extraction_result.category_indicators_found,
            category=extraction_result.category,
        )

    def check_grounding(self, clause: str, contract_text: str) -> bool:
        """Check if a clause appears verbatim in the contract.

        Args:
            clause: The extracted clause text.
            contract_text: The full contract text.

        Returns:
            True if the clause is grounded in the contract.
        """
        # Normalize whitespace for comparison
        normalized_clause = " ".join(clause.split())
        normalized_contract = " ".join(contract_text.split())
        return normalized_clause in normalized_contract

    @observe(name="validation.extract")
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Not used for validation agent - use verify() instead.

        Args:
            contract_text: The contract text.
            category: The CUAD category.
            question: The question prompt.

        Raises:
            NotImplementedError: Always, use verify() instead.
        """
        raise NotImplementedError("Use verify() for validation agent")
