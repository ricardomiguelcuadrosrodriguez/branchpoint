"""Tests for branchpoint.decorators — @trace and @tool wrappers."""
from __future__ import annotations

from pathlib import Path

import pytest

from branchpoint.decorators import tool, trace
from branchpoint.recorder import get_active_recorder, record
from branchpoint.storage import read_events, read_meta


def _latest_session(sessions_dir: Path) -> Path:
    """Returns the most recently created session dir under sessions_dir."""
    dirs = sorted(sessions_dir.iterdir(), key=lambda p: p.name)
    assert dirs, "no session directories were created"
    return dirs[-1]


class TestTraceDecorator:
    def test_nested_in_explicit_session(self, sessions_dir: Path) -> None:
        @trace(name="greet")
        def greet(who: str) -> str:
            return f"hola {who}"

        with record(name="outer", sessions_dir=sessions_dir) as session:
            assert greet("jefe") == "hola jefe"

        events = read_events(session.session_dir)
        types = [e["type"] for e in events]
        assert types == ["session_start", "step_start", "step_end", "session_end"]

        step_start = next(e for e in events if e["type"] == "step_start")
        assert step_start["name"] == "greet"
        assert step_start["args"] == {"who": "jefe"}
        assert step_start["step_id"] == "step-001"

        step_end = next(e for e in events if e["type"] == "step_end")
        assert step_end["status"] == "success"
        assert step_end["result"] == "hola jefe"
        assert step_end["duration_ms"] >= 0

    def test_nested_traces_produce_sequential_step_ids(
        self, sessions_dir: Path
    ) -> None:
        @trace(name="inner")
        def inner(x: int) -> int:
            return x + 1

        @trace(name="outer")
        def outer() -> int:
            return inner(1) + inner(2)

        with record(sessions_dir=sessions_dir) as session:
            assert outer() == 5

        events = read_events(session.session_dir)
        step_starts = [e for e in events if e["type"] == "step_start"]
        step_ids = [e["step_id"] for e in step_starts]
        assert step_ids == ["step-001", "step-002", "step-003"]
        # Inner steps reference the outer as their parent
        outer_step = step_starts[0]
        inner_steps = step_starts[1:]
        assert outer_step["parent_step_id"] is None
        for inner_step in inner_steps:
            assert inner_step["parent_step_id"] == "step-001"

    def test_auto_session_when_no_active_recorder(
        self, sessions_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Redirect DEFAULT_SESSIONS_DIR for the auto-session path
        import branchpoint.recorder as rec_mod
        monkeypatch.setattr(rec_mod, "DEFAULT_SESSIONS_DIR", sessions_dir)

        @trace(name="solo")
        def solo(x: int) -> int:
            return x * 2

        assert solo(21) == 42
        assert get_active_recorder() is None  # session finished

        session_dir = _latest_session(sessions_dir)
        events = read_events(session_dir)
        assert [e["type"] for e in events] == [
            "session_start",
            "step_start",
            "step_end",
            "session_end",
        ]
        assert read_meta(session_dir)["status"] == "success"

    def test_exception_emits_error_and_step_end_error(
        self, sessions_dir: Path
    ) -> None:
        @trace(name="boom")
        def boom() -> None:
            raise ValueError("nope")

        with pytest.raises(ValueError, match="nope"):
            with record(sessions_dir=sessions_dir) as session:
                boom()

        events = read_events(session.session_dir)
        types = [e["type"] for e in events]
        assert "error" in types
        err = next(e for e in events if e["type"] == "error")
        assert err["error_type"] == "ValueError"
        assert err["message"] == "nope"
        assert "ValueError" in err["traceback"]

        step_end = next(e for e in events if e["type"] == "step_end")
        assert step_end["status"] == "error"

        # Outermost (record() ctx) marks the session as errored
        session_end = next(e for e in events if e["type"] == "session_end")
        assert session_end["status"] == "error"

    def test_long_string_result_truncated(self, sessions_dir: Path) -> None:
        @trace(name="bloater")
        def bloater() -> str:
            return "x" * 20_000  # > 8KB

        with record(sessions_dir=sessions_dir) as session:
            bloater()

        events = read_events(session.session_dir)
        step_end = next(e for e in events if e["type"] == "step_end")
        result = step_end["result"]
        assert "<truncated" in result
        assert len(result) < 20_000


class TestToolDecorator:
    def test_emits_tool_call_event(self, sessions_dir: Path) -> None:
        @tool(side_effects=True)
        def save(data: dict) -> str:
            return "saved"

        @trace(name="wrapper")
        def use_tool() -> str:
            return save({"k": "v"})

        with record(sessions_dir=sessions_dir) as session:
            use_tool()

        events = read_events(session.session_dir)
        tool_calls = [e for e in events if e["type"] == "tool_call"]
        assert len(tool_calls) == 1
        tc = tool_calls[0]
        assert tc["tool_name"] == "save"
        assert tc["arguments"] == {"data": {"k": "v"}}
        assert tc["result"] == "saved"
        assert tc["status"] == "success"
        assert tc["has_side_effects"] is True

    def test_tool_metadata_attached(self) -> None:
        @tool(name="custom", side_effects=True)
        def my_tool() -> None:
            pass

        meta = getattr(my_tool, "__branchpoint_tool__")
        assert meta == {"name": "custom", "side_effects": True}

    def test_tool_outside_session_runs_normally(self) -> None:
        @tool()
        def add(a: int, b: int) -> int:
            return a + b

        # No active session → tool just runs, no event emitted, no error
        assert add(2, 3) == 5

    def test_tool_exception_emits_error_status(
        self, sessions_dir: Path
    ) -> None:
        @tool()
        def fails() -> None:
            raise RuntimeError("tool boom")

        @trace(name="wrapper")
        def use_failing_tool() -> None:
            fails()

        with pytest.raises(RuntimeError, match="tool boom"):
            with record(sessions_dir=sessions_dir) as session:
                use_failing_tool()

        events = read_events(session.session_dir)
        tool_calls = [e for e in events if e["type"] == "tool_call"]
        assert len(tool_calls) == 1
        assert tool_calls[0]["status"] == "error"
        assert "RuntimeError" in str(tool_calls[0]["result"])
