"""Prompt registry and template management.

Loads prompts from YAML files in the prompts/ directory.
Supports variable interpolation and versioning.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


# Default prompts directory
PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@dataclass
class PromptTemplate:
    """A prompt template with metadata.

    Attributes:
        name: Unique identifier for the prompt.
        version: Version string for tracking changes.
        description: Human-readable description.
        system: System prompt content.
        user: User prompt template (supports {variables}).
        variables: List of required variable names.
        category_indicators: Optional category-specific indicators.
        metadata: Additional metadata.
    """
    name: str
    version: str = "1.0"
    description: str = ""
    system: str = ""
    user: str = ""
    variables: list[str] = field(default_factory=list)
    category_indicators: dict[str, list[str]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def format(self, **kwargs: Any) -> tuple[str, str]:
        """Format the prompt with variables.

        Args:
            **kwargs: Variable values to interpolate.

        Returns:
            Tuple of (system_prompt, user_prompt).

        Raises:
            KeyError: If required variable is missing.
        """
        # Check required variables
        missing = set(self.variables) - set(kwargs.keys())
        if missing:
            raise KeyError(f"Missing required variables: {missing}")

        system = self.system.format(**kwargs) if self.system else ""
        user = self.user.format(**kwargs) if self.user else ""

        return system, user

    def get_indicators(self, category: str) -> list[str]:
        """Get indicators for a specific category.

        Args:
            category: CUAD category name.

        Returns:
            List of indicator strings.
        """
        return self.category_indicators.get(category, [])

    def format_indicators(self, category: str) -> str:
        """Format indicators as a bullet list.

        Args:
            category: CUAD category name.

        Returns:
            Formatted indicator string.
        """
        indicators = self.get_indicators(category)
        if not indicators:
            return "No specific indicators defined."
        return "\n".join(f"- {ind}" for ind in indicators)


class PromptRegistry:
    """Registry for loading and managing prompts.

    Usage:
        registry = PromptRegistry()
        registry.load_all()  # Load from default directory

        prompt = registry.get("risk_liability")
        system, user = prompt.format(
            category="Cap on Liability",
            contract_text="...",
            question="...",
        )
    """

    def __init__(self, prompts_dir: Path | None = None) -> None:
        """Initialize the registry.

        Args:
            prompts_dir: Directory containing prompt YAML files.
        """
        self.prompts_dir = prompts_dir or PROMPTS_DIR
        self._prompts: dict[str, PromptTemplate] = {}

    def load_all(self) -> None:
        """Load all prompts from the prompts directory."""
        if not self.prompts_dir.exists():
            return

        for yaml_file in self.prompts_dir.rglob("*.yaml"):
            self.load_file(yaml_file)

    def load_file(self, path: Path) -> PromptTemplate | None:
        """Load a prompt from a YAML file.

        Args:
            path: Path to YAML file.

        Returns:
            Loaded PromptTemplate or None if invalid.
        """
        try:
            with open(path) as f:
                data = yaml.safe_load(f)

            if not data or "name" not in data:
                return None

            prompt = PromptTemplate(
                name=data["name"],
                version=data.get("version", "1.0"),
                description=data.get("description", ""),
                system=data.get("system", ""),
                user=data.get("user", ""),
                variables=data.get("variables", []),
                category_indicators=data.get("category_indicators", {}),
                metadata=data.get("metadata", {}),
            )

            self._prompts[prompt.name] = prompt
            return prompt

        except Exception as e:
            print(f"Error loading prompt from {path}: {e}")
            return None

    def get(self, name: str) -> PromptTemplate:
        """Get a prompt by name.

        Args:
            name: Prompt name.

        Returns:
            PromptTemplate instance.

        Raises:
            KeyError: If prompt not found.
        """
        if name not in self._prompts:
            raise KeyError(f"Prompt not found: {name}. Available: {list(self._prompts.keys())}")
        return self._prompts[name]

    def register(self, prompt: PromptTemplate) -> None:
        """Register a prompt directly.

        Args:
            prompt: PromptTemplate to register.
        """
        self._prompts[prompt.name] = prompt

    def list(self) -> list[str]:
        """List all registered prompt names.

        Returns:
            List of prompt names.
        """
        return list(self._prompts.keys())

    def __contains__(self, name: str) -> bool:
        """Check if prompt exists."""
        return name in self._prompts

    def __len__(self) -> int:
        """Number of registered prompts."""
        return len(self._prompts)


# Global registry instance
_registry: PromptRegistry | None = None


def _get_registry() -> PromptRegistry:
    """Get or create global registry."""
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
        _registry.load_all()
    return _registry


def load_prompt(path: Path) -> PromptTemplate | None:
    """Load a prompt from file into global registry.

    Args:
        path: Path to YAML file.

    Returns:
        Loaded PromptTemplate.
    """
    return _get_registry().load_file(path)


def get_prompt(name: str) -> PromptTemplate:
    """Get a prompt from global registry.

    Args:
        name: Prompt name.

    Returns:
        PromptTemplate instance.
    """
    return _get_registry().get(name)


def list_prompts() -> list[str]:
    """List all prompts in global registry.

    Returns:
        List of prompt names.
    """
    return _get_registry().list()
