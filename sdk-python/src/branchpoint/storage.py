"""JSONL storage for traces.

A session directory looks like:

    ~/.branchpoint/sessions/{session_id}/
    ├── trace.jsonl          # event log (append-only)
    ├── meta.json            # summary written on session_end
    └── snapshots/           # state snapshots (Session 6+)
        ├── step-001.pkl
        └── ...

Design notes:
    - trace.jsonl is opened in append mode and fsync'd after each write.
      That makes the trace durable across crashes: the agent can die and
      whatever was written so far survives.
    - meta.json is written atomically (temp file + rename). It's overwritten
      in full on each session_end, not appended.
    - Concurrent writes from multiple threads must be serialized by the
      caller (the Recorder holds a lock per session).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Event log (trace.jsonl)
# ---------------------------------------------------------------------------


def write_event(session_dir: Path, event: dict[str, Any]) -> None:
    """Append one JSON-serialized event to trace.jsonl.

    Crash-safe: the file is fsync'd after every write, so the trace
    survives a process crash up to (and including) the last completed call.
    """
    session_dir.mkdir(parents=True, exist_ok=True)
    trace_path = session_dir / "trace.jsonl"
    line = json.dumps(event, default=_default_encoder, ensure_ascii=False) + "\n"
    # Open with low-level os.open so we can fsync the fd directly.
    fd = os.open(trace_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def read_events(session_dir: Path) -> list[dict[str, Any]]:
    """Read all events from a session's trace.jsonl.

    Skips blank lines. Raises json.JSONDecodeError if a line is malformed
    (we deliberately don't silently drop bad data — callers should know).
    """
    trace_path = session_dir / "trace.jsonl"
    if not trace_path.exists():
        return []
    events: list[dict[str, Any]] = []
    with trace_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


# ---------------------------------------------------------------------------
# Session metadata (meta.json)
# ---------------------------------------------------------------------------


def write_meta(session_dir: Path, meta: dict[str, Any]) -> None:
    """Write meta.json atomically (temp file + rename).

    Atomic rename guarantees readers never see a half-written file. Used by
    `branchpoint sessions list` and the dashboard for fast summaries.
    """
    session_dir.mkdir(parents=True, exist_ok=True)
    meta_path = session_dir / "meta.json"
    # NamedTemporaryFile in the same dir → rename is atomic on POSIX
    fd, tmp_path = tempfile.mkstemp(
        prefix=".meta.", suffix=".json.tmp", dir=session_dir
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(meta, f, default=_default_encoder, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, meta_path)
    except Exception:
        # On failure, clean up the temp file
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def read_meta(session_dir: Path) -> dict[str, Any] | None:
    """Read meta.json. Returns None if the session hasn't finished yet."""
    meta_path = session_dir / "meta.json"
    if not meta_path.exists():
        return None
    with meta_path.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# JSON encoder fallback
# ---------------------------------------------------------------------------


def _default_encoder(obj: Any) -> Any:
    """Encoder fallback for non-JSON-serializable objects.

    Strategy: Pydantic models → model_dump(); objects with __dict__ → dict;
    bytes → length tag; everything else → repr().
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, bytes):
        return f"<bytes len={len(obj)}>"
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return repr(obj)
