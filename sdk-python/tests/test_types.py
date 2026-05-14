"""Test for the trace schema — sanity checks that Pydantic models work.

Real tests for Recorder, decorators, etc. land in Session 2.
"""
from datetime import datetime

import pytest

from branchpoint.types import (
    LLMCallEvent,
    LLMRequest,
    LLMResponse,
    SDKInfo,
    SessionStartEvent,
    StepStartEvent,
    TokenCounts,
    now_iso,
)


def test_session_start_event_validates() -> None:
    event = SessionStartEvent(
        session_id="01HK7XYZ",
        timestamp=now_iso(),
        sdk=SDKInfo(language="python", version="0.0.1"),
        name="test",
    )
    assert event.type == "session_start"
    # JSON round-trip works
    raw = event.model_dump_json()
    assert "session_start" in raw


def test_step_start_event_validates() -> None:
    event = StepStartEvent(
        step_id="step-001",
        timestamp=now_iso(),
        name="my_agent",
        args={"question": "why is the sky blue"},
    )
    assert event.type == "step_start"


def test_llm_call_event_validates() -> None:
    event = LLMCallEvent(
        step_id="step-001",
        call_id="call-001",
        timestamp=now_iso(),
        duration_ms=1234.5,
        provider="anthropic",
        model="claude-sonnet-4-6",
        request=LLMRequest(messages=[{"role": "user", "content": "hi"}]),
        response=LLMResponse(content="hello"),
        tokens=TokenCounts(input=10, output=5),
        cost_usd=0.00015,
    )
    assert event.type == "llm_call"
    assert event.cost_usd == 0.00015


def test_now_iso_returns_string() -> None:
    s = now_iso()
    # ISO 8601 with milliseconds and Z suffix
    assert s.endswith("Z")
    # Parseable
    datetime.fromisoformat(s.replace("Z", "+00:00"))


def test_rejects_extra_fields() -> None:
    """Schema is strict — unexpected keys cause validation errors."""
    with pytest.raises(Exception):
        SessionStartEvent(
            session_id="01HK7XYZ",
            timestamp=now_iso(),
            sdk=SDKInfo(language="python", version="0.0.1"),
            unexpected_field="oops",  # type: ignore[call-arg]
        )
