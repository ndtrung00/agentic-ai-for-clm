"""LangGraph state definitions using TypedDict.

Uses TypedDict instead of dataclass for better LangGraph compatibility.
Supports state annotations for reducers and checkpointing.
"""

from typing import Annotated, Any, TypedDict
from operator import add

from src.agents.base import ExtractionResult


def replace_value(current: Any, new: Any) -> Any:
    """Reducer that replaces the current value with new value."""
    return new


def append_trace(current: list[dict], new: list[dict]) -> list[dict]:
    """Reducer that appends new trace entries."""
    return current + new


class GraphState(TypedDict, total=False):
    """State that flows through the LangGraph workflow.

    Using TypedDict with Annotated reducers for proper state updates.
    This is the recommended LangGraph pattern for complex state.

    Attributes:
        contract_text: The full contract text to analyze.
        category: The CUAD category being extracted.
        question: The question prompt for this category.
        specialist_name: Name of the routed specialist agent.
        extraction_result: Result from specialist extraction.
        validated: Whether extraction passed validation.
        validation_notes: Notes from validation process.
        final_result: Final extraction result after validation.
        trace: Execution trace for explainability.
        error: Error message if something failed.
    """
    # Input - these don't change
    contract_text: str
    category: str
    question: str

    # Routing
    specialist_name: str

    # Extraction
    extraction_result: ExtractionResult | None

    # Validation
    validated: bool
    validation_notes: str

    # Output
    final_result: ExtractionResult | None

    # Trace with append reducer
    trace: Annotated[list[dict[str, Any]], append_trace]

    # Error handling
    error: str | None


class InputState(TypedDict):
    """Input state for the extraction workflow."""
    contract_text: str
    category: str
    question: str


class OutputState(TypedDict):
    """Output state from the extraction workflow."""
    final_result: ExtractionResult | None
    validated: bool
    trace: list[dict[str, Any]]
    error: str | None


def create_initial_state(
    contract_text: str,
    category: str,
    question: str,
) -> GraphState:
    """Create initial state for the workflow.

    Args:
        contract_text: Contract text to analyze.
        category: CUAD category to extract.
        question: Question prompt.

    Returns:
        Initial GraphState.
    """
    return GraphState(
        contract_text=contract_text,
        category=category,
        question=question,
        specialist_name="",
        extraction_result=None,
        validated=False,
        validation_notes="",
        final_result=None,
        trace=[],
        error=None,
    )
