"""JSONL storage for traces.

A session directory looks like:

    ~/.branchpoint/sessions/{session_id}/
    ├── trace.jsonl          # event log (append-only)
    ├── meta.json            # summary computed on session_end
    └── snapshots/
        ├── step-001.pkl
        ├── step-002.pkl
        └── ...

Session 2 implements the writer. This file exists so the Recorder can
import from it without circular deps.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_event(session_dir: Path, event: dict[str, Any]) -> None:
    """Append one JSON-serialized event to trace.jsonl. Fsync-safe."""
    trace_path = session_dir / "trace.jsonl"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=_default_encoder, ensure_ascii=False))
        f.write("\n")
        f.flush()


def read_events(session_dir: Path) -> list[dict[str, Any]]:
    """Read all events from a session's trace.jsonl."""
    trace_path = session_dir / "trace.jsonl"
    if not trace_path.exists():
        return []
    events = []
    with trace_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events


def _default_encoder(obj: Any) -> Any:
    """Encoder fallback for non-JSON-serializable objects.

    Strategy: try `model_dump()` (Pydantic), then `__dict__`, then `repr()`.
    Truncate huge strings/bytes to avoid blowing up the trace.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    if isinstance(obj, bytes):
        return f"<bytes len={len(obj)}>"
    return repr(obj)
