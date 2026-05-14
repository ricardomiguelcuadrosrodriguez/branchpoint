"""Recorder — owns a single session.

The Recorder writes events to JSONL as they happen. It's append-only and
crash-resilient: if your agent dies mid-run, the trace.jsonl up to that
point is still valid.

The full implementation is targeted for Session 2 (see WORK_LOG.md).
This skeleton defines the public surface so other modules can import
without circular deps.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


DEFAULT_SESSIONS_DIR = Path(
    os.environ.get("BRANCHPOINT_DIR", Path.home() / ".branchpoint")
) / "sessions"


class Recorder:
    """Owns one session's trace + snapshots.

    Usage (low-level):
        recorder = Recorder(name="my-agent")
        recorder.start()
        # ... your code ...
        recorder.finish(status="success")

    Most users should prefer `bp.record()` or `@bp.trace`.
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

        # These get populated on .start()
        self.session_id: str | None = None
        self.session_dir: Path | None = None

        # Step counter — incremented on each step_start
        self._step_counter = 0

        # Total cost accumulator
        self._total_cost_usd = 0.0

    # ------------------------------------------------------------------
    # Lifecycle (Session 2 implements this fully)
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open a new session: create dir, write session_start event."""
        raise NotImplementedError("Session 2")

    def finish(self, status: str = "success") -> None:
        """Close the session: write session_end event."""
        raise NotImplementedError("Session 2")

    # ------------------------------------------------------------------
    # Event writers (called by decorators and instrumentation)
    # ------------------------------------------------------------------

    def write_event(self, event: dict[str, Any]) -> None:
        """Append a validated event to trace.jsonl."""
        raise NotImplementedError("Session 2")

    def next_step_id(self) -> str:
        self._step_counter += 1
        return f"step-{self._step_counter:03d}"

    @property
    def cost_usd(self) -> float:
        return self._total_cost_usd


@contextmanager
def record(
    name: str | None = None,
    tags: dict[str, str] | None = None,
) -> Iterator[Recorder]:
    """Context manager for recording a session.

    Example:
        with bp.record(name="my-agent") as session:
            # ... your code ...
            print(f"Cost so far: ${session.cost_usd:.4f}")
    """
    recorder = Recorder(name=name, tags=tags)
    recorder.start()
    try:
        yield recorder
        recorder.finish(status="success")
    except Exception:
        recorder.finish(status="error")
        raise
