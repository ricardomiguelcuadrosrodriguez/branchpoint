/**
 * Trace event schema for branchpoint.
 *
 * This is the canonical schema. The Python SDK uses Pydantic models that
 * MUST match this shape exactly. Treat any divergence as a bug.
 *
 * Stored as JSONL: each line in trace.jsonl is one TraceEvent.
 */

export type ULID = string;
export type ISODateTime = string;

// ---------------------------------------------------------------------------
// Discriminated union of every event type
// ---------------------------------------------------------------------------

export type TraceEvent =
  | SessionStartEvent
  | SessionEndEvent
  | StepStartEvent
  | StepEndEvent
  | LLMCallEvent
  | ToolCallEvent
  | StateSnapshotEvent
  | ErrorEvent;

// ---------------------------------------------------------------------------
// Session-level events (first and last lines of trace.jsonl)
// ---------------------------------------------------------------------------

export interface SessionStartEvent {
  type: "session_start";
  session_id: ULID;
  timestamp: ISODateTime;
  /** Set if this session is a branch from another. */
  parent_session_id?: ULID;
  /** The step we branched from in the parent session. */
  parent_step_id?: string;
  /** User-provided name for the session. */
  name?: string;
  /** Free-form labels. */
  tags?: Record<string, string>;
  sdk: {
    language: "python" | "typescript";
    version: string;
  };
}

export interface SessionEndEvent {
  type: "session_end";
  timestamp: ISODateTime;
  status: "success" | "error" | "aborted";
  total_cost_usd: number;
  total_duration_ms: number;
}

// ---------------------------------------------------------------------------
// Step events (function/scope boundaries)
// ---------------------------------------------------------------------------

export interface StepStartEvent {
  type: "step_start";
  /** Sequential id: "step-001", "step-002", ... */
  step_id: string;
  timestamp: ISODateTime;
  /** For nested steps (a step that called another @trace function). */
  parent_step_id?: string;
  /** Usually the function name. */
  name?: string;
  /** Function arguments, truncated/redacted if huge. */
  args?: Record<string, unknown>;
}

export interface StepEndEvent {
  type: "step_end";
  step_id: string;
  timestamp: ISODateTime;
  duration_ms: number;
  status: "success" | "error";
  /** Return value, truncated if too large. */
  result?: unknown;
}

// ---------------------------------------------------------------------------
// LLM call events (the most important — these are what we replay)
// ---------------------------------------------------------------------------

export interface LLMCallEvent {
  type: "llm_call";
  step_id: string;
  /** Unique within the session. */
  call_id: string;
  timestamp: ISODateTime;
  duration_ms: number;
  provider: "anthropic" | "openai" | "other";
  model: string;
  request: {
    messages: Array<{ role: string; content: unknown }>;
    system?: string;
    temperature?: number;
    max_tokens?: number;
    tools?: unknown[];
    [key: string]: unknown;
  };
  response: {
    content: unknown;
    stop_reason?: string;
    tool_calls?: unknown[];
    [key: string]: unknown;
  };
  tokens: {
    input: number;
    output: number;
    cached?: number;
  };
  /** Computed locally from pricing tables. */
  cost_usd: number;
}

// ---------------------------------------------------------------------------
// Tool call events
// ---------------------------------------------------------------------------

export interface ToolCallEvent {
  type: "tool_call";
  step_id: string;
  call_id: string;
  timestamp: ISODateTime;
  tool_name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  duration_ms: number;
  status: "success" | "error";
  /** User-declared via bp.tool({ sideEffects: true }). */
  has_side_effects?: boolean;
}

// ---------------------------------------------------------------------------
// State snapshots (what enables time travel)
// ---------------------------------------------------------------------------

export interface StateSnapshotEvent {
  type: "state_snapshot";
  step_id: string;
  snapshot_id: string;
  /** Path relative to the session directory. */
  snapshot_path: string;
  size_bytes: number;
  /** "dill" for Python, "superjson" for TypeScript. */
  serializer: "dill" | "superjson";
}

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

export interface ErrorEvent {
  type: "error";
  step_id?: string;
  timestamp: ISODateTime;
  error_type: string;
  message: string;
  /** Stack trace as a single string. */
  traceback: string;
}

// ---------------------------------------------------------------------------
// Derived / aggregate types (computed from the trace, not stored)
// ---------------------------------------------------------------------------

export interface SessionSummary {
  session_id: ULID;
  name?: string;
  started_at: ISODateTime;
  finished_at?: ISODateTime;
  status: "running" | "success" | "error" | "aborted";
  total_cost_usd: number;
  total_duration_ms: number;
  step_count: number;
  llm_call_count: number;
  parent_session_id?: ULID;
  branch_count: number;
  sdk_language: "python" | "typescript";
}

export interface StepSummary {
  step_id: string;
  name?: string;
  started_at: ISODateTime;
  duration_ms: number;
  status: "success" | "error";
  llm_calls: number;
  tool_calls: number;
  cost_usd: number;
  has_snapshot: boolean;
}
