"""Base agent class for contract clause extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from langfuse.decorators import observe
from pydantic import BaseModel


class ExtractionResult(BaseModel):
    """Structured output from clause extraction."""

    extracted_clauses: list[str] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0
    category_indicators_found: list[str] = field(default_factory=list)
    category: str = ""


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.0
    max_tokens: int = 4096
    categories: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the agent with configuration.

        Args:
            config: Agent configuration including model settings.
        """
        self.config = config
        self.name = config.name

    @abstractmethod
    @observe()
    async def extract(
        self,
        contract_text: str,
        category: str,
        question: str,
    ) -> ExtractionResult:
        """Extract clauses from contract text for a given category.

        Args:
            contract_text: The full contract text to analyze.
            category: The CUAD category to extract.
            question: The question prompt for this category.

        Returns:
            ExtractionResult with extracted clauses and reasoning.
        """
        ...

    @abstractmethod
    def get_prompt(self, category: str) -> str:
        """Get the prompt template for a category.

        Args:
            category: The CUAD category.

        Returns:
            The prompt template string.
        """
        ...

    def handles_category(self, category: str) -> bool:
        """Check if this agent handles the given category.

        Args:
            category: The CUAD category to check.

        Returns:
            True if this agent handles the category.
        """
        return category in self.config.categories
