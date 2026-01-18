"""Base agent class for contract clause extraction."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from src.prompts import PromptTemplate, get_prompt
from src.models import ModelDiagnostics


class ExtractionResult(BaseModel):
    """Structured output from clause extraction."""

    extracted_clauses: list[str] = []
    reasoning: str = ""
    confidence: float = 0.0
    category_indicators_found: list[str] = []
    category: str = ""

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    model_key: str = "claude-sonnet"  # Key from model registry
    temperature: float = 0.0
    max_tokens: int = 4096
    categories: list[str] = field(default_factory=list)
    prompt_name: str = ""  # Name of prompt template to use


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Agents use the prompt registry for prompts and model client for LLM calls.
    All agents support diagnostics tracking for model comparison.
    """

    def __init__(
        self,
        config: AgentConfig,
        diagnostics: ModelDiagnostics | None = None,
    ) -> None:
        """Initialize the agent with configuration.

        Args:
            config: Agent configuration including model settings.
            diagnostics: Optional diagnostics collector for tracking.
        """
        self.config = config
        self.name = config.name
        self.diagnostics = diagnostics
        self._prompt_template: PromptTemplate | None = None

    @property
    def prompt_template(self) -> PromptTemplate:
        """Get the prompt template for this agent.

        Returns:
            PromptTemplate instance.
        """
        if self._prompt_template is None:
            prompt_name = self.config.prompt_name or self.config.name
            self._prompt_template = get_prompt(prompt_name)
        return self._prompt_template

    @abstractmethod
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

    def get_prompt(self) -> tuple[str, str]:
        """Get system and user prompts.

        Returns:
            Tuple of (system_prompt, user_prompt_template).
        """
        return self.prompt_template.system, self.prompt_template.user

    def get_indicators(self, category: str) -> str:
        """Get formatted indicators for a category.

        Args:
            category: The CUAD category.

        Returns:
            Formatted indicator string.
        """
        return self.prompt_template.format_indicators(category)

    def handles_category(self, category: str) -> bool:
        """Check if this agent handles the given category.

        Args:
            category: The CUAD category to check.

        Returns:
            True if this agent handles the category.
        """
        return category in self.config.categories

    async def invoke_model(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        category: str = "",
    ) -> str:
        """Invoke the model with diagnostics tracking.

        Args:
            messages: List of message dicts.
            system: Optional system prompt.
            category: Category being processed (for diagnostics).

        Returns:
            Model response text.
        """
        from src.models import invoke_model

        response, _usage = await invoke_model(
            model_key=self.config.model_key,
            messages=messages,
            system=system,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            diagnostics=self.diagnostics,
            agent_name=self.name,
            category=category,
        )
        return response

    def parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from model response.

        Args:
            response: Raw model response text.

        Returns:
            Parsed dictionary.
        """
        import json
        import re

        # Try to extract JSON from response
        # Handle cases where model wraps JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            response = json_match.group(1)

        # Also try to find raw JSON object
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            response = json_match.group(0)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # Return empty dict if parsing fails
            return {}

    def result_from_dict(self, data: dict[str, Any], category: str) -> ExtractionResult:
        """Create ExtractionResult from parsed dict.

        Args:
            data: Parsed response dictionary.
            category: The category being extracted.

        Returns:
            ExtractionResult instance.
        """
        return ExtractionResult(
            extracted_clauses=data.get("extracted_clauses", []),
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 0.0),
            category_indicators_found=data.get("category_indicators_found", []),
            category=category,
        )
