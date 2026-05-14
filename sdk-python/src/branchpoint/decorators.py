"""Public decorators: @trace and @tool.

These wrap user functions to participate in the active recording session.
Full implementations land in Session 2.
"""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar


F = TypeVar("F", bound=Callable[..., Any])


def trace(
    name: str | None = None,
    tags: dict[str, str] | None = None,
) -> Callable[[F], F]:
    """Decorate a function as a top-level traced agent.

    If there's no active session, one is created for the duration of the call.
    If there IS an active session, the function becomes a nested step.

    Example:
        @bp.trace(name="my-agent")
        def my_agent(question: str) -> str:
            ...
    """
    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Session 2: open or join a Recorder, emit step_start, run fn,
            # emit step_end, return result.
            return fn(*args, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator


def tool(
    name: str | None = None,
    side_effects: bool = False,
) -> Callable[[F], F]:
    """Decorate a function as a tool that should be traced and (optionally)
    marked as having side effects.

    Tools marked with `side_effects=True` will trigger a confirmation prompt
    when replayed via the dashboard, since re-running them could duplicate
    writes to external systems.

    Example:
        @bp.tool(side_effects=True)
        def save_to_db(data: dict) -> None:
            db.insert(data)
    """
    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Session 2: emit tool_call event with side_effects flag.
            return fn(*args, **kwargs)
        # Stash metadata for the replay engine
        wrapper.__branchpoint_tool__ = {  # type: ignore[attr-defined]
            "name": name or fn.__name__,
            "side_effects": side_effects,
        }
        return wrapper  # type: ignore[return-value]
    return decorator
