"""Recorder — owns a single session.

The Recorder writes events to JSONL as they happen. It's append-only and
crash-resilient: if your agent dies mid-run, the trace.jsonl up to that
point is still valid.

Usage:

    # As a context manager (recommended):
    with bp.record(name="my-agent") as session:
        ...

    # Low-level:
    recorder = Recorder(name="my-agent")
    recorder.start()
    try:
        ...
    finally:
        recorder.finish(status="success")

Active-recorder tracking
------------------------
The active recorder is stored in a contextvars.ContextVar so that:
  - Async code propagates context correctly (each Task gets its own view).
  - Threads don't accidentally share a recorder.
  - Decorators (`@bp.trace`) can find the recorder without explicit plumbing.

If no recorder is active, `@bp.trace` creates one for the duration of the
decorated function call.
"""
from __future__ import annotations

import contextvars
import os
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import ulid
from pydantic import TypeAdapter, ValidationError

from branchpoint.storage import write_event, write_meta
from branchpoint.types import (
    ErrorEvent,
    SDKInfo,
    SessionEndEvent,
    SessionStartEvent,
    StepEndEvent,
    StepStartEvent,
    TraceEvent,
    now_iso,
)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


DEFAULT_SESSIONS_DIR = Path(
    os.environ.get("BRANCHPOINT_DIR", Path.home() / ".branchpoint")
) / "sessions"


# Active recorder for the current execution context (async-safe, thread-safe).
_active_recorder: contextvars.ContextVar[Recorder | None] = contextvars.ContextVar(
    "branchpoint_active_recorder", default=None
)


# Pydantic validator for the TraceEvent discriminated union.
# We validate every event before it hits disk to catch schema bugs early.
_event_validator: TypeAdapter[TraceEvent] = TypeAdapter(TraceEvent)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_active_recorder() -> Recorder | None:
    """Return the recorder for the current execution context, if any."""
    return _active_recorder.get()


def _sdk_version() -> str:
    # Import lazily to avoid circular imports at module load time
    from branchpoint import __version__
    return __version__


# ---------------------------------------------------------------------------
# Recorder
# ---------------------------------------------------------------------------


class RecorderStateError(RuntimeError):
    """Raised when the Recorder is used in an invalid state."""


class Recorder:
    """Owns one session's trace.jsonl + meta.json (snapshots arrive in Session 6).

    A Recorder is single-use: call .start() once, then .finish() once. Reusing
    a Recorder after finish() raises RecorderStateError.
    """

    def __init__(
        self,
        name: str | None = None,
        tags: dict[str, str] | None = None,
        sessions_dir: Path | None = None,
        parent_session_id: str | None = None,
        parent_step_id: str | None = None,
    ) -> None:
        self.name = name
        self.tags = tags or {}
        self.sessions_dir = sessions_dir or DEFAULT_SESSIONS_DIR
        self.parent_session_id = parent_session_id
        self.parent_step_id = parent_step_id

        # Populated on .start()
        self.session_id: str | None = None
        self.session_dir: Path | None = None
        self._start_monotonic: float | None = None
        self._token: contextvars.Token[Recorder | None] | None = None

        # Counters for meta.json
        self._step_counter = 0
        self._step_count_finished = 0
        self._llm_call_count = 0
        self._tool_call_count = 0
        self._total_cost_usd = 0.0
        self._finished = False

        # Serializes writes from concurrent threads in the same process.
        # ContextVar gives us per-task isolation for "who's active", but
        # file writes still need to be ordered.
        self._write_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open a new session: assign ULID, create dir, write session_start."""
        if self.session_id is not None:
            raise RecorderStateError(
                "Recorder.start() was already called for this session"
            )

        self.session_id = ulid.new().str
        self.session_dir = self.sessions_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._start_monotonic = time.monotonic()

        event = SessionStartEvent(
            session_id=self.session_id,
            timestamp=now_iso(),
            parent_session_id=self.parent_session_id,
            parent_step_id=self.parent_step_id,
            name=self.name,
            tags=self.tags or None,
            sdk=SDKInfo(language="python", version=_sdk_version()),
        )
        self._write(event)
        self._token = _active_recorder.set(self)

    def finish(self, status: str = "success") -> None:
        """Close the session: write session_end + meta.json. Idempotent."""
        if self._finished:
            return
        if self.session_id is None or self.session_dir is None:
            # finish() called without start() — silently no-op rather than
            # raising, because this is most commonly hit in error paths.
            return

        assert self._start_monotonic is not None
        duration_ms = (time.monotonic() - self._start_monotonic) * 1000.0

        end_event = SessionEndEvent(
            timestamp=now_iso(),
            status=status,  # type: ignore[arg-type]  # validated by Pydantic
            total_cost_usd=round(self._total_cost_usd, 6),
            total_duration_ms=round(duration_ms, 3),
        )
        self._write(end_event)

        # Write meta.json for fast dashboard listing
        write_meta(
            self.session_dir,
            {
                "session_id": self.session_id,
                "name": self.name,
                "status": status,
                "started_at": None,  # filled in by aggregator if needed
                "total_cost_usd": round(self._total_cost_usd, 6),
                "total_duration_ms": round(duration_ms, 3),
                "step_count": self._step_count_finished,
                "llm_call_count": self._llm_call_count,
                "tool_call_count": self._tool_call_count,
                "parent_session_id": self.parent_session_id,
                "parent_step_id": self.parent_step_id,
                "sdk": {"language": "python", "version": _sdk_version()},
            },
        )

        self._finished = True
        if self._token is not None:
            _active_recorder.reset(self._token)
            self._token = None

    # ------------------------------------------------------------------
    # Event writers (called by decorators and instrumentation)
    # ------------------------------------------------------------------

    def write_event(self, event: TraceEvent | dict[str, Any]) -> None:
        """Validate and append a trace event.

        Accepts either a Pydantic model instance or a plain dict (which gets
        validated against the TraceEvent union). Bookkeeping (counters,
        cost totals) is updated based on the event type.
        """
        if self.session_id is None or self.session_dir is None:
            raise RecorderStateError(
                "Recorder.write_event() called before .start()"
            )
        if self._finished:
            raise RecorderStateError(
                "Recorder.write_event() called after .finish()"
            )

        # Validate
        try:
            validated = (
                event
                if hasattr(event, "model_dump")
                else _event_validator.validate_python(event)
            )
        except ValidationError as e:
            raise RecorderStateError(f"Invalid event: {e}") from e

        self._write(validated)
        self._update_counters(validated)

    def next_step_id(self) -> str:
        """Allocate the next sequential step id (step-001, step-002, ...)."""
        self._step_counter += 1
        return f"step-{self._step_counter:03d}"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def cost_usd(self) -> float:
        """Running total cost in USD across all LLM calls in this session."""
        return self._total_cost_usd

    @property
    def is_running(self) -> bool:
        return self.session_id is not None and not self._finished

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write(self, event: Any) -> None:
        """Serialize and write the event under the write lock."""
        assert self.session_dir is not None
        payload = event.model_dump(mode="json") if hasattr(event, "model_dump") else event
        with self._write_lock:
            write_event(self.session_dir, payload)

    def _update_counters(self, event: TraceEvent) -> None:
        """Bookkeeping for meta.json totals."""
        # Use the type discriminator from the validated event.
        event_type = event.type  # type: ignore[union-attr]
        if event_type == "step_end":
            self._step_count_finished += 1
        elif event_type == "llm_call":
            self._llm_call_count += 1
            self._total_cost_usd += event.cost_usd  # type: ignore[union-attr]
        elif event_type == "tool_call":
            self._tool_call_count += 1


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


@contextmanager
def record(
    name: str | None = None,
    tags: dict[str, str] | None = None,
    sessions_dir: Path | None = None,
) -> Iterator[Recorder]:
    """Context manager for recording a session.

    Example:
        with bp.record(name="my-agent") as session:
            # ... your code ...
            print(f"Cost so far: ${session.cost_usd:.4f}")
    """
    recorder = Recorder(name=name, tags=tags, sessions_dir=sessions_dir)
    recorder.start()
    try:
        yield recorder
    except BaseException:
        recorder.finish(status="error")
        raise
    else:
        recorder.finish(status="success")
