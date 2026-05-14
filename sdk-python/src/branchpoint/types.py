"""Trace event schema for branchpoint (Python).

This MUST match `sdk-typescript/src/types.ts` exactly. Any divergence is a bug.

Stored as JSONL — each line in trace.jsonl is one event.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Common type aliases
# ---------------------------------------------------------------------------

ULID = str
ISODateTime = str


# ---------------------------------------------------------------------------
# Base event (every event has a `type` discriminator)
# ---------------------------------------------------------------------------

class _BaseEvent(BaseModel):
    """Internal base — never instantiated directly."""
    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Session-level events
# ---------------------------------------------------------------------------

class SDKInfo(BaseModel):
    language: Literal["python", "typescript"]
    version: str


class SessionStartEvent(_BaseEvent):
    type: Literal["session_start"] = "session_start"
    session_id: ULID
    timestamp: ISODateTime
    parent_session_id: ULID | None = None
    parent_step_id: str | None = None
    name: str | None = None
    tags: dict[str, str] | None = None
    sdk: SDKInfo


class SessionEndEvent(_BaseEvent):
    type: Literal["session_end"] = "session_end"
    timestamp: ISODateTime
    status: Literal["success", "error", "aborted"]
    total_cost_usd: float
    total_duration_ms: float


# ---------------------------------------------------------------------------
# Step events (function/scope boundaries)
# ---------------------------------------------------------------------------

class StepStartEvent(_BaseEvent):
    type: Literal["step_start"] = "step_start"
    step_id: str
    timestamp: ISODateTime
    parent_step_id: str | None = None
    name: str | None = None
    args: dict[str, Any] | None = None


class StepEndEvent(_BaseEvent):
    type: Literal["step_end"] = "step_end"
    step_id: str
    timestamp: ISODateTime
    duration_ms: float
    status: Literal["success", "error"]
    result: Any | None = None


# ---------------------------------------------------------------------------
# LLM call events (the critical ones — these are what we replay)
# ---------------------------------------------------------------------------

class LLMRequest(BaseModel):
    """Arbitrary kwargs for the LLM call. We capture everything for replay."""
    messages: list[dict[str, Any]]
    system: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    tools: list[Any] | None = None

    model_config = {"extra": "allow"}  # capture all provider-specific args


class LLMResponse(BaseModel):
    content: Any
    stop_reason: str | None = None
    tool_calls: list[Any] | None = None

    model_config = {"extra": "allow"}


class TokenCounts(BaseModel):
    input: int
    output: int
    cached: int | None = None


class LLMCallEvent(_BaseEvent):
    type: Literal["llm_call"] = "llm_call"
    step_id: str
    call_id: str
    timestamp: ISODateTime
    duration_ms: float
    provider: Literal["anthropic", "openai", "other"]
    model: str
    request: LLMRequest
    response: LLMResponse
    tokens: TokenCounts
    cost_usd: float


# ---------------------------------------------------------------------------
# Tool call events
# ---------------------------------------------------------------------------

class ToolCallEvent(_BaseEvent):
    type: Literal["tool_call"] = "tool_call"
    step_id: str
    call_id: str
    timestamp: ISODateTime
    tool_name: str
    arguments: dict[str, Any]
    result: Any | None = None
    duration_ms: float
    status: Literal["success", "error"]
    has_side_effects: bool | None = None


# ---------------------------------------------------------------------------
# State snapshots
# ---------------------------------------------------------------------------

class StateSnapshotEvent(_BaseEvent):
    type: Literal["state_snapshot"] = "state_snapshot"
    step_id: str
    snapshot_id: str
    snapshot_path: str
    size_bytes: int
    serializer: Literal["dill", "superjson"]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ErrorEvent(_BaseEvent):
    type: Literal["error"] = "error"
    step_id: str | None = None
    timestamp: ISODateTime
    error_type: str
    message: str
    traceback: str


# ---------------------------------------------------------------------------
# Discriminated union (the value of each line in trace.jsonl)
# ---------------------------------------------------------------------------

TraceEvent = (
    SessionStartEvent
    | SessionEndEvent
    | StepStartEvent
    | StepEndEvent
    | LLMCallEvent
    | ToolCallEvent
    | StateSnapshotEvent
    | ErrorEvent
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """Returns current UTC time as an ISO 8601 string."""
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


# ---------------------------------------------------------------------------
# Derived / aggregate types (computed from a session's trace, not stored)
# ---------------------------------------------------------------------------

class SessionSummary(BaseModel):
    session_id: ULID
    name: str | None = None
    started_at: ISODateTime
    finished_at: ISODateTime | None = None
    status: Literal["running", "success", "error", "aborted"]
    total_cost_usd: float
    total_duration_ms: float
    step_count: int
    llm_call_count: int
    parent_session_id: ULID | None = None
    branch_count: int
    sdk_language: Literal["python", "typescript"]


class StepSummary(BaseModel):
    step_id: str
    name: str | None = None
    started_at: ISODateTime
    duration_ms: float
    status: Literal["success", "error"]
    llm_calls: int
    tool_calls: int
    cost_usd: float
    has_snapshot: bool
