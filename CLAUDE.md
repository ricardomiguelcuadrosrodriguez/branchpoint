# Branchpoint — Complete Project Context

> **Single source of truth.** Combines the public README, the AI handoff context, and the work log into one document. Read top-to-bottom on first contact with the project.

**Status:** Pre-alpha. Scaffolding done, no real code yet (just skeletons with `NotImplementedError("Session N")` markers).
**Owner:** Ricardo Miguel Cuadros Rodriguez (Lima, Perú)
**Repo:** github.com/ricardomiguelcuadrosrodriguez/branchpoint (to be created)
**License:** MIT
**Tagline:** *Git for AI agent runs. Branch from any step, change anything, replay.*

---

# Part 1 — The Project

## 1. What it is

**Branchpoint** is an open-source, self-hosted **time-travel debugger for AI agents**. Like `git branch` but for LLM agent runs.

The differentiator: **counterfactual debugging**. You record an agent run, then click any step in the timeline, edit the prompt/model/parameters at that step, and re-execute from that point forward — without re-running the previous steps. Compare branches side-by-side to find what works.

### The problem it solves

In May 2026, every dev is building agents (Anthropic, OpenAI Agents SDK, LangGraph, CrewAI, Pydantic AI). When an agent fails:

- ❌ Hard to find WHERE it went wrong in a 50-step trace
- ❌ Hard to test "what if I changed the prompt at step 3?" without re-running everything
- ❌ Non-deterministic (temperature > 0) makes bugs hard to reproduce
- ❌ Existing tools (LangSmith, Langfuse, AgentOps) **only record**, they don't let you branch and re-execute with modifications
- ❌ Microsoft Research published AGDebugger (CHI 2025) showing devs WANT this capability — but it's a research paper, no production product exists

The hole in the market: **counterfactual debugging with state-preserving re-execution**. Everyone records. Nobody lets you branch.

## 2. Demo flow (what users will see)

```
Your agent runs:
  step 1 → step 2 → step 3 → step 4 → step 5 → ❌ failed

branchpoint records everything to ~/.branchpoint/sessions/, including
a snapshot of state at each step.

You open the dashboard, click step 3, modify the prompt, hit "Branch":
  step 1 ─┬─→ step 2 → step 3  → step 4  → step 5  → ❌ failed (original)
          └─→ step 2 → step 3' → step 4' → step 5' → ✅ success (your branch)

The branch runs from step 3 with your changes, reusing the state
snapshot from step 2 instead of re-running steps 1-2.
```

## 3. Public API

### Python

```python
import branchpoint as bp
import anthropic

@bp.trace(name="my-agent")
def my_agent(question: str) -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text

my_agent("Why is the sky blue?")
# Trace saved to ~/.branchpoint/sessions/

# Open the dashboard:
# $ branchpoint dashboard
```

Other entry points:
```python
# Explicit session control
with bp.record(name="my-agent") as session:
    # ... your code ...
    print(f"Cost so far: ${session.cost_usd:.4f}")

# Mark side-effect tools (skip on replay or confirm)
@bp.tool(side_effects=True)
def save_to_db(data: dict) -> None:
    db.insert(data)
```

### TypeScript

```typescript
import * as bp from "@branchpoint/sdk";
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const myAgent = bp.trace("my-agent", async (question: string) => {
  const response = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 512,
    messages: [{ role: "user", content: question }],
  });
  const block = response.content[0];
  return block.type === "text" ? block.text : "";
});

await myAgent("Why is the sky blue?");
```

### CLI

```bash
$ pip install branchpoint
$ branchpoint dashboard         # opens http://localhost:3089
$ branchpoint sessions list
$ branchpoint session show <id>
```

## 4. Differentiation vs the market

| | LangSmith | Langfuse | AgentOps | **Branchpoint** |
|---|---|---|---|---|
| Self-hosted | ❌ | ✅ | ❌ | ✅ |
| Observability | ✅ | ✅ | ✅ | ✅ |
| Cost tracking | ✅ | ✅ | ✅ | ✅ |
| **Branch from step N + edit + replay** | ❌ | ❌ | ❌ | ✅ |
| **Side-by-side comparison** | ❌ | ❌ | ❌ | ✅ |
| Free forever | ❌ | ✅ | ❌ | ✅ |
| Python + TypeScript | ✅ | ✅ | partial | ✅ |

**Academic validation:** Microsoft Research's [AGDebugger paper](https://arxiv.org/abs/2503.02068) (CHI 2025) shows devs want counterfactual debugging. No production OSS tool exists. We're filling the hole.

---

# Part 2 — Architecture

## 5. Stack

**SDK Python (`sdk-python/`):**
- Python 3.10+
- `pyproject.toml` (hatchling, modern)
- `dill` for state snapshots (handles closures better than pickle)
- `pydantic` v2 for trace schema
- Anthropic + OpenAI SDKs as optional dependencies
- `httpx` for HTTP capture (optional)
- `click` + `rich` for CLI

**SDK TypeScript (`sdk-typescript/`):**
- TypeScript 5.7
- ESM-only (no CommonJS)
- Node 20+
- `superjson` for state serialization
- Same trace schema (shared spec)
- Patches `@anthropic-ai/sdk` and `openai` packages

**Backend (`server/`):** *(implemented in Session 5)*
- FastAPI + Python 3.10+
- SQLite for sessions index
- Filesystem (`.branchpoint/`) for trace JSONL + state snapshots
- WebSocket support for live tail

**Frontend (`web/`):** *(implemented in Session 5)*
- Next.js 15, React 19, TypeScript strict
- Tailwind v3 (NOT v4)
- `lucide-react` icons
- `monaco-editor` for prompt editing + diff
- `recharts` for cost timeline
- NO shadcn (custom design like Whendo)
- Palette: bg/ink/lime/flame (from Whendo) + **indigo `#7C7CFF` for branches**

## 6. High-level architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       USER'S MACHINE                            │
│                                                                 │
│   User's agent code  ──┐                                        │
│        ▼                │                                       │
│   @bp.trace decorator   │                                       │
│        ▼                │                                       │
│   Recorder ───┬─────────┤                                       │
│               │         │                                       │
│   Patched     │         │                                       │
│   anthropic ──┤         │                                       │
│   openai   ───┤         │                                       │
│               ▼         ▼                                       │
│         ~/.branchpoint/sessions/                                │
│         ├── 2026-05-13-14-32-01.session/                        │
│         │   ├── trace.jsonl       (chronological event log)     │
│         │   ├── meta.json         (cost, duration, status)      │
│         │   └── snapshots/        (state at each step, dill)    │
│         │       ├── step-001.pkl                                │
│         │       └── ...                                         │
│         └── 2026-05-13-14-32-01.branches/                       │
│             ├── branch-a-from-step-3.session/                   │
│             └── branch-b-from-step-3.session/                   │
│                                                                 │
│                          ▲                                      │
│                          │                                      │
│   ┌──────────────────────┴──────────────────────┐               │
│   │      Backend (FastAPI :8089)                │               │
│   │      - GET /api/sessions                    │               │
│   │      - GET /api/sessions/{id}/trace         │               │
│   │      - POST /api/sessions/{id}/branch       │               │
│   │      - WS  /api/sessions/{id}/live          │               │
│   └─────────────────────────────────────────────┘               │
│                          ▲                                      │
│                          │                                      │
│   ┌──────────────────────┴──────────────────────┐               │
│   │      Dashboard (Next.js :3089)              │               │
│   │      Open via `branchpoint dashboard`       │               │
│   └─────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

> **Ports 8089/3089** (not 8000/3000) to avoid colliding with Whendo running in parallel.

## 7. Repo structure

```
branchpoint/
├── README.md                       # Public-facing intro
├── LICENSE (MIT)
├── CLAUDE.md                       # THIS FILE (unified context)
├── WORK_LOG.md                     # Running session log
├── .gitignore
│
├── assets/
│   └── logo.png                    # TBD
│
├── docs/
│   ├── architecture.md
│   ├── trace-schema.md
│   ├── branching.md
│   └── README.es.md
│
├── sdk-python/
│   ├── pyproject.toml
│   ├── README.md
│   ├── src/branchpoint/
│   │   ├── __init__.py             # Public API: trace, record, tool
│   │   ├── recorder.py             # Recorder class — owns a session
│   │   ├── decorators.py           # @trace, @tool
│   │   ├── instrument/
│   │   │   ├── __init__.py
│   │   │   ├── anthropic.py        # Auto-patches anthropic SDK
│   │   │   └── openai.py           # Auto-patches openai SDK
│   │   ├── storage.py              # JSONL writer + session dir mgmt
│   │   ├── snapshot.py             # dill-based state snapshots
│   │   ├── pricing.py              # Token pricing tables
│   │   ├── types.py                # Pydantic models for events
│   │   ├── replay.py               # Replay/branch engine
│   │   └── cli.py                  # `branchpoint dashboard` command
│   └── tests/
│       ├── test_types.py           # 5 passing tests
│       └── test_pricing.py         # 8 passing tests
│
├── sdk-typescript/
│   ├── package.json                # ESM-only
│   ├── tsconfig.json
│   ├── README.md
│   ├── src/
│   │   ├── index.ts                # Public API
│   │   ├── recorder.ts
│   │   ├── decorators.ts
│   │   ├── instrument/             # Patches @anthropic-ai/sdk + openai
│   │   ├── storage.ts
│   │   ├── snapshot.ts             # superjson-based
│   │   ├── pricing.ts
│   │   ├── types.ts                # CANONICAL schema (Python copies)
│   │   └── replay.ts
│   └── tests/
│
├── server/                         # Session 5
│   ├── pyproject.toml
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── sessions.py
│   │   ├── branches.py
│   │   └── cost.py
│   ├── db/
│   │   └── index.py                # SQLite index of sessions on disk
│   └── branching/
│       └── engine.py               # Orchestrates re-execution
│
├── web/                            # Session 5
│   ├── package.json
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                # Sessions list
│   │   └── sessions/[id]/
│   │       ├── page.tsx
│   │       └── compare/page.tsx
│   ├── components/
│   │   ├── SessionTimeline.tsx
│   │   ├── StepDetail.tsx
│   │   ├── PromptEditor.tsx
│   │   ├── BranchButton.tsx
│   │   ├── CostChart.tsx
│   │   └── DiffViewer.tsx
│   └── lib/api.ts
│
└── examples/
    ├── python/
    │   ├── 01-basic-agent.py       ✅ exists
    │   ├── 02-tool-using-agent.py  ✅ exists
    │   └── 03-multi-step-research.py
    └── typescript/
        ├── 01-basic-agent.ts       ✅ exists
        └── 02-tool-using-agent.ts
```

## 8. Trace schema (the contract)

This is the **most important spec** in the project. Both SDKs MUST produce JSONL events that conform exactly. Stored under `.branchpoint/sessions/{session_id}/trace.jsonl`.

```typescript
// Each line in trace.jsonl is one event
type TraceEvent =
  | SessionStartEvent
  | SessionEndEvent
  | StepStartEvent
  | StepEndEvent
  | LLMCallEvent
  | ToolCallEvent
  | StateSnapshotEvent
  | ErrorEvent;

type SessionStartEvent = {
  type: "session_start";
  session_id: string;          // ULID
  timestamp: string;           // ISO 8601
  parent_session_id?: string;  // set if this is a branch
  parent_step_id?: string;     // the step we branched from
  name?: string;
  tags?: Record<string, string>;
  sdk: { language: "python" | "typescript"; version: string };
};

type StepStartEvent = {
  type: "step_start";
  step_id: string;             // sequential: "step-001"
  timestamp: string;
  parent_step_id?: string;
  name?: string;
  args?: Record<string, unknown>;
};

type StepEndEvent = {
  type: "step_end";
  step_id: string;
  timestamp: string;
  duration_ms: number;
  status: "success" | "error";
  result?: unknown;
};

type LLMCallEvent = {
  type: "llm_call";
  step_id: string;
  call_id: string;
  timestamp: string;
  duration_ms: number;
  provider: "anthropic" | "openai" | "other";
  model: string;
  request: {
    messages: Array<{ role: string; content: unknown }>;
    system?: string;
    temperature?: number;
    max_tokens?: number;
    tools?: unknown[];
  };
  response: {
    content: unknown;
    stop_reason?: string;
    tool_calls?: unknown[];
  };
  tokens: { input: number; output: number; cached?: number };
  cost_usd: number;            // computed locally from pricing table
};

type ToolCallEvent = {
  type: "tool_call";
  step_id: string;
  call_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  result?: unknown;
  duration_ms: number;
  status: "success" | "error";
  has_side_effects?: boolean;
};

type StateSnapshotEvent = {
  type: "state_snapshot";
  step_id: string;
  snapshot_id: string;
  snapshot_path: string;
  size_bytes: number;
  serializer: "dill" | "superjson";
};

type ErrorEvent = {
  type: "error";
  step_id?: string;
  timestamp: string;
  error_type: string;
  message: string;
  traceback: string;
};

type SessionEndEvent = {
  type: "session_end";
  timestamp: string;
  status: "success" | "error" | "aborted";
  total_cost_usd: number;
  total_duration_ms: number;
};
```

**Rules:**
- Append-only. Once written, an event is never modified.
- Every `step_end` has a matching `step_start` with same `step_id`.
- LLM/Tool call events reference their parent `step_id`.
- Branches are NEW sessions with `parent_session_id` + `parent_step_id` filled.
- The full request/response of LLM calls is captured for verbatim or modified replay.

## 9. State snapshotting (the hardest part — Session 6)

This is what enables "branch from step N without re-running steps 1..N-1".

### Strategy

At the END of each step, serialize the relevant state:
- Local variables of the traced function
- The conversation history accumulated so far
- Any user-declared "context object" passed via `bp.context()`

**Python:** Use `dill` (handles closures, generators, lambdas).
**TypeScript:** Use `superjson` for structured cloneable values + a "manifest" of refs for non-serializable things. Fail loudly when something can't be restored.

### When the user clicks "Branch from step N"

1. Load snapshot from `step-N`
2. Re-create the execution environment (re-import modules, etc.)
3. Inject the snapshot as starting state
4. Execute step N+1 onwards with the user's modifications
5. Write new JSONL events as a NEW session
6. Link the new session via `parent_session_id` + `parent_step_id`

### What CAN'T be replayed (side effects)

If a step did `db.insert(...)`, replaying it would duplicate.

- **Explicit:** `@bp.tool(side_effects=True)` → on replay, confirm via UI
- **Auto-detection (heuristic):** HTTP POST/PUT/DELETE/PATCH, SQLAlchemy writes → warn
- **Pure (LLM-only):** safe to replay automatically

### Known limitations (document upfront)

- Replay with `temperature > 0` gives different results each time.
- External APIs may change between record and replay.
- Files written to disk during the run aren't time-traveled.

---

# Part 3 — Decisions Already Made

> Don't relitigate these without strong evidence. Each one was deliberate.

1. **Two SDKs from day 1 (Python + TS).** Double work, but TS is huge for AI agents now (Vercel AI SDK, OpenAI Agents JS, Mastra).
2. **Same trace schema for both SDKs.** Defined in TS, mirrored in Python via Pydantic. Interop is the moat.
3. **Local-first, no cloud version in v1.** Cloud comes later if traction proves out.
4. **Counterfactual is THE feature.** Without branch+modify+replay, we shouldn't ship.
5. **Auto-instrumentation of Anthropic + OpenAI from day 1.** Frameworks (LangGraph, CrewAI) are v2.
6. **Filesystem + SQLite. No Postgres.** Self-hosted = simple.
7. **JSONL append-only for traces.** Never modify a written line.
8. **No accounts, no auth, no users in v1.** Dev tool you run on your laptop.
9. **`dill` for Python, `superjson` for TS.** Best-effort serialization with clear failure modes.
10. **MIT license.** No source-available, no commercial license complexity.
11. **Ports 8089 (server) and 3089 (web).** Avoid colliding with Whendo (8000/3000).
12. **NO shadcn/ui.** Custom design.
13. **Indigo `#7C7CFF` is the "branch" color.** Lime is current run, flame is action, indigo is alternate paths.
14. **Naming: "sessions" not "runs" or "traces".** Sessions matches developer mental model.

---

# Part 4 — Work Log

## Session 1 — Scaffolding (May 13, 2026) ✅ DONE

**Goal:** Set up structure, schemas, skeleton code.

**Done:**
- ✅ Repo structure designed
- ✅ `CLAUDE.md` (this file)
- ✅ `README.md`, `LICENSE`, `.gitignore`
- ✅ **Trace schema** in `sdk-typescript/src/types.ts` (canonical) and `sdk-python/src/branchpoint/types.py` (parity)
- ✅ Python SDK skeleton (pyproject.toml, all 11 module files, 2 test files with 13 passing tests)
- ✅ TypeScript SDK skeleton (package.json, tsconfig.json, 4 source files)
- ✅ 3 examples (2 Python, 1 TS)
- ✅ Pricing tables for Claude 4.x + GPT-4o/o3 (real numbers, May 2026)
- ✅ All files validated, 0 syntax errors

**Decisions captured:** see Part 3 above.

**State at end of session:**
- 32 files total
- Nothing runs end-to-end yet
- Imports work, types valid, tests pass for types + pricing
- Ready for Session 2

## Session 2 — Python SDK Recorder (NEXT)

**Goal:** Make `bp.record()` and `@bp.trace` actually work — write valid trace.jsonl to disk.

**Plan:**
1. Implement `Recorder.start()`:
   - Generate ULID for session_id
   - Create `sessions_dir / session_id /`
   - Write `SessionStartEvent` to `trace.jsonl`
2. Implement `Recorder.finish()`:
   - Compute total duration
   - Write `SessionEndEvent` with final cost + status
3. Implement `Recorder.write_event()`:
   - Validate via Pydantic
   - Append to trace.jsonl via `storage.write_event()`
4. Wire up `@bp.trace` decorator:
   - Use `contextvars.ContextVar` for the active Recorder
   - On entry: emit `StepStartEvent`
   - Time the call
   - On exit: emit `StepEndEvent` with status + duration
   - On exception: emit `ErrorEvent` + `StepEndEvent(status=error)` + re-raise
5. Same for `@bp.tool`:
   - Emit `ToolCallEvent` with `side_effects` flag
6. Write `meta.json` on `finish()` for fast dashboard listing
7. Tests:
   - `test_recorder.py`: open/close session, validate JSONL, schema checks
   - `test_decorators.py`: nested @trace produces nested step_ids
   - `test_storage.py`: concurrent writes are safe
8. Update example `01-basic-agent.py` to write a real trace

**Acceptance:**
- Run `python examples/python/01-basic-agent.py` → produces `~/.branchpoint/sessions/<ulid>/trace.jsonl` with 4 events: `session_start`, `step_start`, `step_end`, `session_end`
- `pytest sdk-python/tests/` → 10+ passing tests
- `branchpoint sessions list` → shows the session

**Estimated effort:** 10-14 hours.

## Session 3 — TypeScript SDK (parity with Python)

**Goal:** Same surface as Session 2 but in TypeScript.

**Plan:**
1. Implement `Recorder.start()` / `.finish()` / `.writeEvent()`
2. Use `AsyncLocalStorage` (Node) for active Recorder context
3. Implement `trace()` and `tool()` wrappers
4. Same JSONL format as Python
5. `vitest` tests
6. Make `01-basic-agent.ts` work end-to-end

**Acceptance:**
- TS example produces JSONL byte-compatible with Python output
- Both languages show in `branchpoint sessions list`

## Session 4 — Auto-instrumentation

**Goal:** When user calls `anthropic.messages.create()` inside `@bp.trace`, emit `llm_call` automatically.

**Plan:**
1. Python: monkey-patch `anthropic.resources.messages.Messages.create` (sync + async)
2. Python: same for `openai.resources.chat.completions.Completions.create` + Responses API
3. TS: patch `@anthropic-ai/sdk` and `openai` package
4. Capture: full request kwargs, full response, tokens, duration
5. Compute cost from `pricing.py`
6. Emit `LLMCallEvent`
7. Handle streaming (accumulate, emit at end)
8. Tests with mocks

**Acceptance:**
- Real Anthropic API call → see `llm_call` events with full request/response/cost
- `branchpoint sessions show <id>` → prints timeline with costs

## Session 5 — Backend + dashboard (observability only)

**Goal:** Working web UI to browse sessions. NO branching yet.

**Plan:**
1. FastAPI server in `server/main.py`
2. Endpoints:
   - `GET /api/sessions` → list of `SessionSummary`
   - `GET /api/sessions/{id}` → full trace events
   - `GET /api/sessions/{id}/summary`
   - `GET /health`
3. Read directly from `~/.branchpoint/sessions/`
4. `branchpoint dashboard` starts FastAPI + Next.js
5. Next.js pages: `/` (list), `/sessions/[id]` (timeline + detail)
6. Reuse Whendo's visual style + indigo `#7C7CFF` for branches
7. Cost chart with recharts

**Acceptance:**
- Open `http://localhost:3089` after running an example
- See session in list → click → see timeline → click step → see prompt + response
- Costs in USD

## Session 6 — Branching & replay (THE feature) — 2-3 weekends

**Goal:** Click any step, edit the prompt, re-execute from that point. Compare branches side-by-side.

**Plan:**
1. Python state snapshots:
   - At end of each `@bp.trace`, dill-pickle user's context
   - Store `snapshots/{step_id}.pkl`, compress with zstd
   - Emit `StateSnapshotEvent`
2. Branch API:
   - `POST /api/sessions/{id}/branch` body `{from_step, modifications}`
   - Server spawns subprocess: `python -m branchpoint.replay --session <id> --from-step <s> --mods <json>`
   - Subprocess loads snapshot, applies mods, runs from step, writes new session
   - Returns new session_id
3. UI:
   - Click step → "Branch from here" button
   - Monaco editor for the LLM request body
   - Submit → API → poll for new session → open it
4. Compare view:
   - `/sessions/[id]/compare?with=<branchId>` → side-by-side
   - Monaco diff editor for prompts
   - Diff costs, durations, outputs
5. Side-effect tools:
   - On replay, pause via WebSocket: "this tool has side effects, run anyway?"
6. **Demo video** — 30-45s OBS recording
7. **Launch:**
   - Show HN: *"Show HN: Branchpoint – Git for AI agent runs"*
   - r/MachineLearning, r/LocalLLaMA
   - X thread with GIFs
   - dev.to blog post
8. **Polish:** target 50+ stars in first 24h, reply to every HN comment

**Acceptance:**
- Demo video shows: real session → click step → edit prompt → re-execute → branch appears → side-by-side
- README has the GIF embedded
- Public repo, MIT, clear quickstart

## After v0.1 (don't start until launch is done)

- LangGraph + CrewAI + Pydantic AI integrations
- TS state snapshots: superjson + manifest of non-serializable refs
- Evaluation mode: run a branch against a dataset, score win rate
- VS Code extension: inline dashboard
- Cloud sync (opt-in, encrypted)
- Team features (only if there's demand)

---

# Part 5 — Conventions and Style

## Naming
- **Python:** snake_case
- **TypeScript:** camelCase, types PascalCase
- **JSONL events:** snake_case keys (Python idiom, fine in TS)
- **Packages:** `branchpoint` (Python), `@branchpoint/sdk` (TypeScript)
- **CLI:** `branchpoint <subcommand>`

## Commit messages
Conventional Commits:
- `feat(python-sdk): add Recorder class`
- `feat(ts-sdk): parity with Python Recorder`
- `feat(web): session timeline component`
- `fix(snapshot): handle dill failures gracefully`

## Tests
- Python: `pytest` in `sdk-python/tests/`
- TypeScript: `vitest` in `sdk-typescript/tests/`
- E2E (later): Playwright

## Tone of docs
- README: vendor mode (sell the value), badges, demo GIF
- Inline comments: explain "why", not "what"
- Examples are tested — they MUST run without modification

---

# Part 6 — Working With Ricardo

- **Language:** casual Spanish from Peru. Code and docs in English.
- **Level:** senior developer. Skip basics. DO explain architectural tradeoffs.
- **Preferences:**
  - Honest. Call bad ideas bad.
  - Concrete. Copy-paste commands when possible.
  - Structured with headers when multiple points.
  - No unnecessary apologies.
- **Doesn't like:** vague answers, sycophancy, hidden mistakes, "claro!" without substance.
- **Likes:** pointing out problems he didn't see, concrete improvements, "honestly, this might fail because..."
- Has other projects (Kora ERP, Cia, Whendo). Branchpoint is **independent**. Don't mix.

---

# Part 7 — How to Run It

**Prerequisites:** Python 3.10+, Node 20+, Git

```bash
# Clone
git clone <repo>
cd branchpoint

# Python SDK
cd sdk-python
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
# → 13 tests should pass (types + pricing)

# TypeScript SDK
cd ../sdk-typescript
pnpm install
pnpm test

# Run a Python example (Session 2+)
cd ../examples/python
python 01-basic-agent.py

# Open dashboard (Session 5+)
branchpoint dashboard   # opens http://localhost:3089
```

---

# Part 8 — Gotchas to Remember

- **Don't import user's agent code from the server.** Server reads files; re-execution happens via SDK in a subprocess.
- **Snapshots can be HUGE.** 50-step session = 100MB+. Compress with zstd early. Limit snapshot to user-declared "context", not all globals.
- **`dill` can't serialize everything.** Database connections, open file handles, threadpools, sockets. Fallback: serialize what we can, manifest of what we couldn't, warn on replay.
- **OpenAI and Anthropic SDKs evolve.** Pin minimum versions, but be defensive — response shapes change. Test against current + N-1.
- **TS decorators are experimental.** Use wrapper functions (`bp.trace(name, fn)`) instead of `@bp.trace`.
- **Side-effect detection is heuristic.** Can't statically guarantee. Always warn on replay if not explicitly marked.

---

# Part 9 — Files Critical to Read Before Modifying

1. `sdk-typescript/src/types.ts` — **canonical schema**. Don't break compatibility.
2. `sdk-python/src/branchpoint/types.py` — must match TS schema exactly.
3. `sdk-python/src/branchpoint/recorder.py` — core recording logic.
4. `server/api/sessions.py` — dashboard API.
5. `web/components/SessionTimeline.tsx` — main UI component.

**If you modify the trace schema, you MUST:**
- Update both `types.ts` and `types.py`
- Bump SDK version (semver minor for additive, major for breaking)
- Update `docs/trace-schema.md`
- Add migration note if breaking

---

# Part 10 — Known Limitations (Be Honest)

- 🚧 **Non-deterministic replay.** Re-running with `temperature > 0` gives different results.
- 🚧 **Side effects on replay.** Marked tools pause for confirmation; unmarked can duplicate writes.
- 🚧 **TS snapshots are weaker than Python.** `superjson` doesn't handle closures the way `dill` does.
- 🚧 **Framework integrations are post-v0.1.** Direct SDK calls work; LangGraph/CrewAI come after.

---

# Part 11 — Acknowledgments

- Microsoft Research's [AGDebugger paper](https://arxiv.org/abs/2503.02068) (CHI 2025) — academic validation of counterfactual debugging.
- OpenTelemetry community for auto-instrumentation patterns we borrow.
- LangSmith and Langfuse for showing what observability dashboards should look like; we're building the missing time-travel layer.

---

# End of Context

If you have questions before making changes, ask. If you're about to make a significant change, propose it first. **Consistency with prior decisions matters more than "perfectly elegant" new code.**

**Last updated:** May 13, 2026
**Last completed session:** Session 1 — scaffolding
**Next session:** Session 2 — Python SDK Recorder + JSONL storage + tests
