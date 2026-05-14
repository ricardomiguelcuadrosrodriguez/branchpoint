"""Public decorators: @trace and @tool.

These wrap user functions to participate in the active recording session.

    @bp.trace(name="my-agent")
    def my_agent(question: str) -> str:
        ...

    @bp.tool(side_effects=True)
    def save_to_db(data: dict) -> None:
        ...

Semantics
---------
@trace:
  - If no recorder is active, one is created for the duration of the call
    (auto-session). The session_id is fresh and the trace goes to the
    default sessions directory.
  - If a recorder IS active, the function becomes a nested step in the
    current session. step_id is allocated by the recorder.
  - On exception: emits an ErrorEvent + StepEndEvent(status="error") and
    re-raises. The session is still finished cleanly (either success or
    error depending on the outermost frame).

@tool:
  - Always nested inside an active session. If no session is active, the
    tool just runs normally (no events emitted) — we deliberately don't
    spin up a session for a single tool call.
  - Emits one ToolCallEvent on completion (or exception, with status="error").
  - The `side_effects` flag is stored on the wrapper (`__branchpoint_tool__`)
    so the replay engine can decide whether to skip / confirm on replay.

Argument capture
----------------
We capture the *names* of arguments when introspection succeeds (via
`inspect.signature`) and fall back to positional indices ("arg0", "arg1")
otherwise. Values are serialized best-effort by storage._default_encoder.
"""
from __future__ import annotations

import inspect
import time
import traceback as tb_mod
import ulid
from functools import wraps
from typing import Any, Callable, TypeVar

from branchpoint.recorder import Recorder, get_active_recorder
from branchpoint.types import (
    ErrorEvent,
    StepEndEvent,
    StepStartEvent,
    ToolCallEvent,
    now_iso,
)


F = TypeVar("F", bound=Callable[..., Any])


# ---------------------------------------------------------------------------
# @trace
# ---------------------------------------------------------------------------


def trace(
    name: str | None = None,
    tags: dict[str, str] | None = None,
) -> Callable[[F], F]:
    """Decorate a function as a traced step.

    If there's no active session, one is created for the duration of the call
    and finished automatically (auto-session). If a session is already active,
    the function becomes a nested step inside it.

    Example:
        @bp.trace(name="my-agent")
        def my_agent(question: str) -> str:
            ...
    """

    def decorator(fn: F) -> F:
        step_name = name or fn.__name__

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            recorder = get_active_recorder()
            owns_session = recorder is None

            if recorder is None:
                # Auto-session: create one just for this call.
                recorder = Recorder(name=step_name, tags=tags)
                recorder.start()

            try:
                return _run_step(recorder, fn, step_name, args, kwargs)
            finally:
                if owns_session and recorder.is_running:
                    # Status was set inside _run_step via finish_on_error;
                    # if we get here without an exception, we mark success.
                    # Note: _run_step already wrote the step events.
                    if not recorder._finished:  # type: ignore[attr-defined]
                        recorder.finish(status="success")

        return wrapper  # type: ignore[return-value]

    return decorator


def _run_step(
    recorder: Recorder,
    fn: Callable[..., Any],
    step_name: str,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    """Emit step_start, run fn, emit step_end (or error). Re-raises on failure.

    Shared implementation between @trace's auto-session and nested-step paths.
    """
    step_id = recorder.next_step_id()
    parent_step_id = getattr(recorder, "_current_step_id", None)

    captured_args = _capture_args(fn, args, kwargs)

    start_event = StepStartEvent(
        step_id=step_id,
        timestamp=now_iso(),
        parent_step_id=parent_step_id,
        name=step_name,
        args=captured_args,
    )
    recorder.write_event(start_event)

    # Track parent step for nested traces (simple stack on the recorder).
    previous_step_id = getattr(recorder, "_current_step_id", None)
    recorder._current_step_id = step_id  # type: ignore[attr-defined]

    started = time.monotonic()
    try:
        result = fn(*args, **kwargs)
    except BaseException as exc:
        duration_ms = (time.monotonic() - started) * 1000.0
        # ErrorEvent first, then StepEndEvent(status="error")
        recorder.write_event(
            ErrorEvent(
                step_id=step_id,
                timestamp=now_iso(),
                error_type=type(exc).__name__,
                message=str(exc),
                traceback=tb_mod.format_exc(),
            )
        )
        recorder.write_event(
            StepEndEvent(
                step_id=step_id,
                timestamp=now_iso(),
                duration_ms=round(duration_ms, 3),
                status="error",
                result=None,
            )
        )
        recorder._current_step_id = previous_step_id  # type: ignore[attr-defined]
        # If this was the outermost step, mark session as errored.
        if previous_step_id is None and not recorder._finished:  # type: ignore[attr-defined]
            recorder.finish(status="error")
        raise

    duration_ms = (time.monotonic() - started) * 1000.0
    recorder.write_event(
        StepEndEvent(
            step_id=step_id,
            timestamp=now_iso(),
            duration_ms=round(duration_ms, 3),
            status="success",
            result=_safe_serialize(result),
        )
    )
    recorder._current_step_id = previous_step_id  # type: ignore[attr-defined]
    return result


# ---------------------------------------------------------------------------
# @tool
# ---------------------------------------------------------------------------


def tool(
    name: str | None = None,
    side_effects: bool = False,
) -> Callable[[F], F]:
    """Decorate a function as a tool that should be traced.

    Tools marked with `side_effects=True` will trigger a confirmation prompt
    when replayed via the dashboard.

    Example:
        @bp.tool(side_effects=True)
        def save_to_db(data: dict) -> None:
            db.insert(data)
    """

    def decorator(fn: F) -> F:
        tool_name = name or fn.__name__

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            recorder = get_active_recorder()
            if recorder is None:
                # No active session — just run the tool normally.
                return fn(*args, **kwargs)

            step_id = getattr(recorder, "_current_step_id", None) or recorder.next_step_id()
            call_id = ulid.new().str
            captured_args = _capture_args(fn, args, kwargs)

            started = time.monotonic()
            try:
                result = fn(*args, **kwargs)
            except BaseException as exc:
                duration_ms = (time.monotonic() - started) * 1000.0
                recorder.write_event(
                    ToolCallEvent(
                        step_id=step_id,
                        call_id=call_id,
                        timestamp=now_iso(),
                        tool_name=tool_name,
                        arguments=captured_args,
                        result=f"<error: {type(exc).__name__}: {exc}>",
                        duration_ms=round(duration_ms, 3),
                        status="error",
                        has_side_effects=side_effects,
                    )
                )
                raise

            duration_ms = (time.monotonic() - started) * 1000.0
            recorder.write_event(
                ToolCallEvent(
                    step_id=step_id,
                    call_id=call_id,
                    timestamp=now_iso(),
                    tool_name=tool_name,
                    arguments=captured_args,
                    result=_safe_serialize(result),
                    duration_ms=round(duration_ms, 3),
                    status="success",
                    has_side_effects=side_effects,
                )
            )
            return result

        # Stash metadata for the replay engine
        wrapper.__branchpoint_tool__ = {  # type: ignore[attr-defined]
            "name": tool_name,
            "side_effects": side_effects,
        }
        return wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_args(
    fn: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Best-effort capture of a function call's arguments by name.

    Returns a dict suitable for storage in StepStartEvent.args. Values are
    serialized later by the storage encoder, so non-JSON-safe values are OK.
    """
    try:
        sig = inspect.signature(fn)
        bound = sig.bind_partial(*args, **kwargs)
        # bound.arguments preserves insertion order
        return dict(bound.arguments)
    except (TypeError, ValueError):
        # Fall back to positional + kwargs if signature inspection fails
        captured: dict[str, Any] = {f"arg{i}": v for i, v in enumerate(args)}
        captured.update(kwargs)
        return captured


def _safe_serialize(value: Any) -> Any:
    """Trim huge results so they don't bloat the trace.

    JSON-serializable values pass through. Strings longer than 8KB are
    truncated with a marker. Pydantic models are dumped. Everything else
    falls through to the storage encoder.
    """
    MAX_STR = 8 * 1024
    if isinstance(value, str) and len(value) > MAX_STR:
        return value[:MAX_STR] + f"... <truncated {len(value) - MAX_STR} chars>"
    return value
