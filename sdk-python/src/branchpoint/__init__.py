"""branchpoint — time-travel debugger for AI agents.

Public API:

    @bp.trace(name="my-agent")
    def my_agent(question: str) -> str:
        ...

    with bp.record(name="my-agent") as session:
        ...

    @bp.tool(side_effects=True)
    def save_to_db(data: dict) -> None:
        ...

    # CLI:
    $ branchpoint dashboard
"""
from branchpoint.decorators import trace, tool
from branchpoint.recorder import Recorder, record
from branchpoint.types import (
    LLMCallEvent,
    SessionStartEvent,
    SessionSummary,
    StepStartEvent,
    ToolCallEvent,
    TraceEvent,
)

__version__ = "0.0.1"

__all__ = [
    # Decorators / context managers
    "trace",
    "tool",
    "record",
    # Core class (advanced usage)
    "Recorder",
    # Types
    "LLMCallEvent",
    "SessionStartEvent",
    "SessionSummary",
    "StepStartEvent",
    "ToolCallEvent",
    "TraceEvent",
    # Metadata
    "__version__",
]
