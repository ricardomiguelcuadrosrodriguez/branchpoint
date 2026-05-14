/**
 * trace() and tool() — wrapper functions that participate in recording.
 *
 * We use wrapper functions instead of TC39 decorators because:
 * - Stage 3 decorators have inconsistent runtime support in 2026
 * - Wrappers work everywhere (Node, Bun, Deno) without transpilation flags
 */

/**
 * Wrap an async function so it's recorded when a session is active.
 *
 * Example:
 *   const myAgent = bp.trace("my-agent", async (q: string) => { ... });
 *   await myAgent("hello");
 */
export function trace<Args extends unknown[], R>(
  name: string,
  fn: (...args: Args) => Promise<R>,
  options?: { tags?: Record<string, string> },
): (...args: Args) => Promise<R> {
  return async (...args: Args): Promise<R> => {
    // Session 3 implements: get or create the active Recorder,
    // emit step_start, run fn, emit step_end, return result.
    return fn(...args);
  };
}

/**
 * Mark a function as a tool that should be traced.
 *
 * If `sideEffects: true`, replaying this tool via the dashboard will
 * pause for user confirmation (to avoid duplicating DB writes etc.).
 *
 * Example:
 *   const saveToDb = bp.tool(
 *     { name: "save_to_db", sideEffects: true },
 *     async (data: object) => { await db.insert(data); },
 *   );
 */
export function tool<Args extends unknown[], R>(
  options: { name?: string; sideEffects?: boolean },
  fn: (...args: Args) => Promise<R>,
): (...args: Args) => Promise<R> {
  const wrapper = async (...args: Args): Promise<R> => {
    // Session 3 implements: emit tool_call event with sideEffects flag.
    return fn(...args);
  };
  // Stash metadata for the replay engine to find
  (wrapper as unknown as { __branchpointTool?: unknown }).__branchpointTool = {
    name: options.name ?? fn.name,
    sideEffects: options.sideEffects ?? false,
  };
  return wrapper;
}
