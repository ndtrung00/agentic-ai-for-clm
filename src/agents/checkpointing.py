"""LangGraph checkpointing for debugging and state persistence.

Supports:
- In-memory checkpointing for debugging
- SQLite checkpointing for persistence
- State inspection and replay
"""

from typing import Any
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver


def get_memory_checkpointer() -> MemorySaver:
    """Get an in-memory checkpointer for debugging.

    Use this for development and testing.
    State is lost when the process exits.

    Returns:
        MemorySaver instance.
    """
    return MemorySaver()


def get_sqlite_checkpointer(
    db_path: str | Path = "checkpoints.db",
) -> SqliteSaver:
    """Get a SQLite checkpointer for persistence.

    Use this for production or when you need to:
    - Resume workflows after crashes
    - Inspect historical states
    - Debug failed executions

    Args:
        db_path: Path to SQLite database file.

    Returns:
        SqliteSaver instance.
    """
    import sqlite3
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(conn)


class CheckpointInspector:
    """Utility for inspecting checkpointed states.

    Usage:
        inspector = CheckpointInspector(checkpointer)
        states = inspector.list_checkpoints(thread_id)
        state = inspector.get_state(thread_id, checkpoint_id)
    """

    def __init__(self, checkpointer: MemorySaver | SqliteSaver) -> None:
        """Initialize inspector.

        Args:
            checkpointer: The checkpointer to inspect.
        """
        self.checkpointer = checkpointer

    def list_threads(self) -> list[str]:
        """List all thread IDs with checkpoints.

        Returns:
            List of thread IDs.
        """
        # Implementation depends on checkpointer type
        if isinstance(self.checkpointer, MemorySaver):
            return list(self.checkpointer.storage.keys())
        else:
            # SQLite implementation would query the database
            return []

    def get_latest_state(self, thread_id: str) -> dict[str, Any] | None:
        """Get the latest state for a thread.

        Args:
            thread_id: Thread identifier.

        Returns:
            Latest state dict or None.
        """
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = self.checkpointer.get(config)
        if checkpoint:
            return checkpoint.get("channel_values", {})
        return None

    def get_trace(self, thread_id: str) -> list[dict[str, Any]]:
        """Get the execution trace for a thread.

        Args:
            thread_id: Thread identifier.

        Returns:
            List of trace entries.
        """
        state = self.get_latest_state(thread_id)
        if state:
            return state.get("trace", [])
        return []


def create_thread_config(
    thread_id: str,
    checkpoint_ns: str = "",
) -> dict[str, Any]:
    """Create a config dict for a specific thread.

    Args:
        thread_id: Unique identifier for this execution.
        checkpoint_ns: Optional namespace for checkpoints.

    Returns:
        Config dict for graph.invoke().
    """
    config: dict[str, Any] = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    if checkpoint_ns:
        config["configurable"]["checkpoint_ns"] = checkpoint_ns
    return config
