"""Tests for branchpoint.storage — JSONL writer + meta.json writer."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import pytest

from branchpoint.storage import (
    _default_encoder,
    read_events,
    read_meta,
    write_event,
    write_meta,
)


class TestWriteEvent:
    def test_creates_dir_if_missing(self, tmp_path: Path) -> None:
        session_dir = tmp_path / "does" / "not" / "exist"
        write_event(session_dir, {"type": "session_start", "session_id": "01H"})
        assert (session_dir / "trace.jsonl").exists()

    def test_appends_one_line_per_event(self, tmp_path: Path) -> None:
        write_event(tmp_path, {"type": "step_start", "step_id": "step-001"})
        write_event(tmp_path, {"type": "step_end", "step_id": "step-001"})
        lines = (tmp_path / "trace.jsonl").read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["type"] == "step_start"
        assert json.loads(lines[1])["type"] == "step_end"

    def test_round_trip_via_read_events(self, tmp_path: Path) -> None:
        write_event(tmp_path, {"type": "a", "value": 1})
        write_event(tmp_path, {"type": "b", "value": 2})
        events = read_events(tmp_path)
        assert events == [
            {"type": "a", "value": 1},
            {"type": "b", "value": 2},
        ]

    def test_unicode_preserved(self, tmp_path: Path) -> None:
        write_event(tmp_path, {"type": "x", "name": "español 🇵🇪"})
        events = read_events(tmp_path)
        assert events[0]["name"] == "español 🇵🇪"

    def test_concurrent_writes_dont_corrupt(self, tmp_path: Path) -> None:
        """50 threads writing 10 events each → 500 valid JSON lines."""
        def writer(thread_id: int) -> None:
            for i in range(10):
                write_event(tmp_path, {"type": "x", "thread": thread_id, "i": i})

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        events = read_events(tmp_path)
        assert len(events) == 500
        # Every event is valid JSON with the expected shape
        for e in events:
            assert set(e.keys()) == {"type", "thread", "i"}


class TestReadEvents:
    def test_returns_empty_when_no_file(self, tmp_path: Path) -> None:
        assert read_events(tmp_path) == []

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        trace = tmp_path / "trace.jsonl"
        trace.write_text('{"type":"a"}\n\n{"type":"b"}\n\n')
        assert read_events(tmp_path) == [{"type": "a"}, {"type": "b"}]

    def test_raises_on_malformed_line(self, tmp_path: Path) -> None:
        trace = tmp_path / "trace.jsonl"
        trace.write_text('{"type":"a"}\nNOT JSON\n')
        with pytest.raises(json.JSONDecodeError):
            read_events(tmp_path)


class TestWriteMeta:
    def test_atomic_replace(self, tmp_path: Path) -> None:
        write_meta(tmp_path, {"session_id": "01H", "status": "success"})
        meta = read_meta(tmp_path)
        assert meta == {"session_id": "01H", "status": "success"}

    def test_overwrite_replaces_completely(self, tmp_path: Path) -> None:
        write_meta(tmp_path, {"a": 1, "b": 2})
        write_meta(tmp_path, {"a": 3})  # b is gone
        assert read_meta(tmp_path) == {"a": 3}

    def test_no_temp_file_left_behind(self, tmp_path: Path) -> None:
        write_meta(tmp_path, {"x": 1})
        leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".meta.")]
        assert leftovers == []

    def test_read_meta_returns_none_when_missing(self, tmp_path: Path) -> None:
        assert read_meta(tmp_path) is None


class TestDefaultEncoder:
    def test_pydantic_model_dumped(self) -> None:
        from branchpoint.types import SDKInfo
        sdk = SDKInfo(language="python", version="0.0.1")
        assert _default_encoder(sdk) == {"language": "python", "version": "0.0.1"}

    def test_bytes_replaced_with_length_tag(self) -> None:
        assert _default_encoder(b"x" * 100) == "<bytes len=100>"

    def test_object_with_dict_returns_dict(self) -> None:
        class Foo:
            def __init__(self) -> None:
                self.a = 1

        assert _default_encoder(Foo()) == {"a": 1}

    def test_fallback_to_repr(self) -> None:
        # set has no __dict__ and no model_dump
        assert _default_encoder({1, 2, 3}).startswith("{")
