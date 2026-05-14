/**
 * @branchpoint/sdk — time-travel debugger for AI agents.
 *
 * Public API:
 *
 *   const myAgent = bp.trace("my-agent", async (q: string) => { ... });
 *
 *   await bp.record({ name: "my-agent" }, async (session) => { ... });
 *
 *   const saveToDb = bp.tool({ name: "save_to_db", sideEffects: true }, async (data) => { ... });
 */

export { trace } from "./decorators.js";
export { tool } from "./decorators.js";
export { record, Recorder } from "./recorder.js";

export type {
  TraceEvent,
  SessionStartEvent,
  SessionEndEvent,
  StepStartEvent,
  StepEndEvent,
  LLMCallEvent,
  ToolCallEvent,
  StateSnapshotEvent,
  ErrorEvent,
  SessionSummary,
  StepSummary,
} from "./types.js";

export const VERSION = "0.0.1";
