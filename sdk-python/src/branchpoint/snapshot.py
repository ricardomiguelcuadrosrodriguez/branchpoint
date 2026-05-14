"""State snapshots for time travel.

At the end of each step, we serialize the user's "context" so we can
replay from that point later. Uses `dill` because it handles closures,
lambdas, and generators better than stdlib `pickle`.

Limits:
- Can't snapshot: open file handles, DB connections, threadpools, sockets
- Large objects (>100MB) trigger a warning
- Snapshots are compressed with zstd to save disk space

Full implementation in Session 6.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


SNAPSHOT_VERSION = 1


def take_snapshot(
    context: dict[str, Any],
    session_dir: Path,
    step_id: str,
) -> dict[str, Any]:
    """Pickle the context dict to snapshots/{step_id}.pkl.

    Returns a manifest dict to embed in the StateSnapshotEvent:
        {
            "snapshot_id": str,
            "snapshot_path": "snapshots/step-001.pkl",
            "size_bytes": int,
            "serializer": "dill",
        }

    Session 6 implements this. Until then, we just return a placeholder so
    other code can import without failure.
    """
    raise NotImplementedError("Session 6")


def restore_snapshot(session_dir: Path, snapshot_path: str) -> dict[str, Any]:
    """Load the pickled context from disk."""
    raise NotImplementedError("Session 6")
