/**
 * Recorder — owns a single session.
 *
 * Mirrors the Python Recorder API. Full implementation in Session 3.
 */
import { homedir } from "node:os";
import { join } from "node:path";

const DEFAULT_SESSIONS_DIR = join(
  process.env.BRANCHPOINT_DIR ?? join(homedir(), ".branchpoint"),
  "sessions",
);

export interface RecorderOptions {
  name?: string;
  tags?: Record<string, string>;
  sessionsDir?: string;
  parentSessionId?: string;
  parentStepId?: string;
}

export class Recorder {
  readonly name?: string;
  readonly tags: Record<string, string>;
  readonly sessionsDir: string;
  readonly parentSessionId?: string;
  readonly parentStepId?: string;

  sessionId?: string;
  sessionDir?: string;

  private stepCounter = 0;
  private totalCostUsd = 0;

  constructor(opts: RecorderOptions = {}) {
    this.name = opts.name;
    this.tags = opts.tags ?? {};
    this.sessionsDir = opts.sessionsDir ?? DEFAULT_SESSIONS_DIR;
    this.parentSessionId = opts.parentSessionId;
    this.parentStepId = opts.parentStepId;
  }

  /** Open a new session. Session 3 implements. */
  async start(): Promise<void> {
    throw new Error("Session 3");
  }

  /** Close the session. Session 3 implements. */
  async finish(status: "success" | "error" | "aborted" = "success"): Promise<void> {
    throw new Error("Session 3");
  }

  /** Append a validated event to trace.jsonl. */
  async writeEvent(event: Record<string, unknown>): Promise<void> {
    throw new Error("Session 3");
  }

  nextStepId(): string {
    this.stepCounter += 1;
    return `step-${String(this.stepCounter).padStart(3, "0")}`;
  }

  get costUsd(): number {
    return this.totalCostUsd;
  }
}

/**
 * Run an async function within a recording session.
 *
 * Example:
 *   await bp.record({ name: "my-agent" }, async (session) => {
 *     // ... agent code ...
 *     console.log(`Cost: $${session.costUsd}`);
 *   });
 */
export async function record<T>(
  options: RecorderOptions,
  fn: (session: Recorder) => Promise<T>,
): Promise<T> {
  const recorder = new Recorder(options);
  await recorder.start();
  try {
    const result = await fn(recorder);
    await recorder.finish("success");
    return result;
  } catch (err) {
    await recorder.finish("error");
    throw err;
  }
}
