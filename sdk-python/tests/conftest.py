"""Shared pytest fixtures for branchpoint tests."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    """Per-test sessions directory under tmp_path.

    Tests should pass this explicitly to Recorder/record() to avoid touching
    the user's real ~/.branchpoint/ directory.
    """
    d = tmp_path / "sessions"
    d.mkdir()
    return d
