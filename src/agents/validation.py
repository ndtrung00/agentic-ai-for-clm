"""Validation agent for grounding and format verification."""

from langfuse.decorators import observe

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

        Args:
            extraction_result: The result to validate.
            contract_text: Original contract for grounding check.
            category: The CUAD category for relevance check.

        Returns:
            Validated (potentially corrected) ExtractionResult.
        """
        # TODO: Implement validation logic with LLM
        raise NotImplementedError("Validation not yet implemented")

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
