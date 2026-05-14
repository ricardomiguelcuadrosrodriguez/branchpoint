"""Tests for branchpoint.recorder — session lifecycle, ContextVar, write_event."""
from __future__ import annotations

from pathlib import Path

import pytest

from branchpoint.recorder import (
    Recorder,
    RecorderStateError,
    get_active_recorder,
    record,
)
from branchpoint.storage import read_events, read_meta
from branchpoint.types import (
    LLMCallEvent,
    LLMRequest,
    LLMResponse,
    StepStartEvent,
    TokenCounts,
    now_iso,
)


class TestRecorderLifecycle:
    def test_start_creates_session_dir_and_writes_session_start(
        self, sessions_dir: Path
    ) -> None:
        r = Recorder(name="x", sessions_dir=sessions_dir)
        r.start()
        try:
            assert r.session_id is not None
            assert len(r.session_id) == 26  # ULID length
            assert r.session_dir.exists()
            events = read_events(r.session_dir)
            assert len(events) == 1
            assert events[0]["type"] == "session_start"
            assert events[0]["session_id"] == r.session_id
            assert events[0]["sdk"] == {"language": "python", "version": "0.0.1"}
        finally:
            r.finish()

    def test_finish_writes_session_end_and_meta(self, sessions_dir: Path) -> None:
        r = Recorder(name="x", sessions_dir=sessions_dir)
        r.start()
        r.finish(status="success")

        events = read_events(r.session_dir)
        assert events[-1]["type"] == "session_end"
        assert events[-1]["status"] == "success"
        assert events[-1]["total_cost_usd"] == 0.0
        assert events[-1]["total_duration_ms"] >= 0.0

        meta = read_meta(r.session_dir)
        assert meta is not None
        assert meta["session_id"] == r.session_id
        assert meta["name"] == "x"
        assert meta["status"] == "success"
        assert meta["step_count"] == 0
        assert meta["llm_call_count"] == 0
        assert meta["tool_call_count"] == 0
        assert meta["sdk"] == {"language": "python", "version": "0.0.1"}

    def test_finish_is_idempotent(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        r.start()
        r.finish()
        r.finish()  # second call is a no-op
        events = read_events(r.session_dir)
        end_events = [e for e in events if e["type"] == "session_end"]
        assert len(end_events) == 1

    def test_start_twice_raises(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        r.start()
        with pytest.raises(RecorderStateError):
            r.start()
        r.finish()

    def test_write_event_before_start_raises(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        with pytest.raises(RecorderStateError):
            r.write_event(StepStartEvent(step_id="step-001", timestamp=now_iso()))

    def test_write_event_after_finish_raises(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        r.start()
        r.finish()
        with pytest.raises(RecorderStateError):
            r.write_event(StepStartEvent(step_id="step-001", timestamp=now_iso()))

    def test_finish_without_start_is_noop(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        r.finish()  # no error, no file written
        assert r.session_id is None
        assert not sessions_dir.iterdir() or len(list(sessions_dir.iterdir())) == 0


class TestRecorderActiveContext:
    def test_no_active_recorder_by_default(self) -> None:
        assert get_active_recorder() is None

    def test_start_sets_active(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        r.start()
        try:
            assert get_active_recorder() is r
        finally:
            r.finish()

    def test_finish_clears_active(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        r.start()
        r.finish()
        assert get_active_recorder() is None


class TestRecorderEventValidation:
    def test_invalid_event_rejected(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        r.start()
        try:
            with pytest.raises(RecorderStateError):
                r.write_event({"type": "nonsense_event"})
        finally:
            r.finish()

    def test_dict_event_validated_and_written(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        r.start()
        try:
            r.write_event(
                {
                    "type": "step_start",
                    "step_id": "step-001",
                    "timestamp": now_iso(),
                    "name": "x",
                }
            )
        finally:
            r.finish()
        events = read_events(r.session_dir)
        assert any(e["type"] == "step_start" for e in events)

    def test_llm_call_updates_cost(self, sessions_dir: Path) -> None:
        r = Recorder(sessions_dir=sessions_dir)
        r.start()
        try:
            r.write_event(
                LLMCallEvent(
                    step_id="step-001",
                    call_id="call-001",
                    timestamp=now_iso(),
                    duration_ms=100.0,
                    provider="anthropic",
                    model="claude-sonnet-4-6",
                    request=LLMRequest(messages=[{"role": "user", "content": "hi"}]),
                    response=LLMResponse(content="hello"),
                    tokens=TokenCounts(input=10, output=5),
                    cost_usd=0.0123,
                )
            )
            assert r.cost_usd == pytest.approx(0.0123)
        finally:
            r.finish()

        meta = read_meta(r.session_dir)
        assert meta["llm_call_count"] == 1
        assert meta["total_cost_usd"] == pytest.approx(0.0123)


class TestRecordContextManager:
    def test_success_path(self, sessions_dir: Path) -> None:
        with record(name="x", sessions_dir=sessions_dir) as session:
            assert get_active_recorder() is session

        meta = read_meta(session.session_dir)
        assert meta["status"] == "success"
        assert get_active_recorder() is None

    def test_exception_path(self, sessions_dir: Path) -> None:
        with pytest.raises(RuntimeError, match="boom"):
            with record(name="x", sessions_dir=sessions_dir) as session:
                raise RuntimeError("boom")

        meta = read_meta(session.session_dir)
        assert meta["status"] == "error"
        assert get_active_recorder() is None
