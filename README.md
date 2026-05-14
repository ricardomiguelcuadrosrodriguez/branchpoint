<div align="center">

<img src="./assets/logo.png" alt="branchpoint" width="180" />

# branchpoint

### *Git for AI agent runs. Branch from any step, change anything, replay.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node 20+](https://img.shields.io/badge/node-20+-green.svg)](https://nodejs.org/)
[![Self-hosted](https://img.shields.io/badge/100%25-self--hosted-success.svg)](#quickstart)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#roadmap)

**An open-source, self-hosted time-travel debugger for AI agents.**

[Quickstart](#quickstart) · [How it works](#how-it-works) · [Demo](#demo) · [Roadmap](#roadmap) · [🇪🇸 Español](./docs/README.es.md)

</div>

---

## 🤔 What is this?

Your AI agent failed at step 14 of a 20-step run. You want to know:

- 🪲 **Where exactly did it go wrong?**
- 🔀 **What if I changed the prompt at step 7?**
- 🆚 **Does GPT-4 work better than Claude at step 12?**

Existing tools (LangSmith, Langfuse, AgentOps) **only record**. They show you the trace, but you can't *change and re-execute*. You have to re-run everything from scratch and hope the bug reproduces.

**branchpoint lets you branch from any step**, modify what you want (the prompt, the model, the temperature), and re-execute from that point forward — **without re-running steps 1..N-1**. Then compare branches side-by-side to find what works.

It's `git branch` but for agent runs.

## 🎬 Demo

> [Placeholder GIF: timeline → click step 7 → edit prompt → branch → see new branch run in 2 seconds → compare original vs branch side-by-side]

## ⚡ Quickstart

### Python

```bash
pip install branchpoint
```

```python
import branchpoint as bp
import anthropic

@bp.trace(name="my-agent")
def my_agent(question: str):
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": question}],
    )
    return response.content[0].text

my_agent("Why is the sky blue?")

# Now open the dashboard
# $ branchpoint dashboard
```

### TypeScript

```bash
npm install @branchpoint/sdk
```

```typescript
import * as bp from "@branchpoint/sdk";
import Anthropic from "@anthropic-ai/sdk";

const myAgent = bp.trace("my-agent", async (question: string) => {
  const client = new Anthropic();
  const response = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 1024,
    messages: [{ role: "user", content: question }],
  });
  return response.content[0].text;
});

await myAgent("Why is the sky blue?");
```

That's it. No accounts, no API keys to us, no telemetry. Traces are saved locally to `~/.branchpoint/sessions/`.

### Open the dashboard

```bash
branchpoint dashboard
# Opens http://localhost:3089
```

You'll see your sessions, click any step, edit the prompt, hit "branch from here" — and watch the agent re-run from that exact point.

## 🎯 Why branchpoint?

| | LangSmith | Langfuse | AgentOps | **branchpoint** |
|---|---|---|---|---|
| Self-hosted | ❌ | ✅ | ❌ | ✅ |
| Observability | ✅ | ✅ | ✅ | ✅ |
| Cost tracking | ✅ | ✅ | ✅ | ✅ |
| **Branch from step N + edit + replay** | ❌ | ❌ | ❌ | ✅ |
| **Side-by-side comparison** | ❌ | ❌ | ❌ | ✅ |
| Free forever | ❌ | ✅ | ❌ | ✅ |
| Auto-instruments Anthropic | ✅ | ✅ | ✅ | ✅ |
| Auto-instruments OpenAI | ✅ | ✅ | ✅ | ✅ |
| Python + TypeScript | ✅ | ✅ | partial | ✅ |

**The differentiator:** counterfactual debugging. Microsoft Research [validated the pattern](https://arxiv.org/abs/2503.02068) (CHI 2025), but no production-ready open-source tool exists. Until now.

## 🛠️ How it works

```
Your agent runs:
  step 1 → step 2 → step 3 → step 4 → step 5 → ❌ failed

branchpoint records everything to ~/.branchpoint/sessions/, including
a snapshot of state at each step.

You open the dashboard, click step 3, modify the prompt, hit "Branch":
  step 1 ─┬─→ step 2 → step 3  → step 4  → step 5  → ❌ failed (original)
          └─→ step 2 → step 3' → step 4' → step 5' → ✅ success (your branch)

The branch runs from step 3 with your changes, reusing the
state snapshot from step 2 instead of re-running steps 1-2.
```

**Key design choices:**

- ✅ **Local-first.** Traces stored in `~/.branchpoint/sessions/`. Your data never leaves your machine.
- ✅ **Same trace schema for Python & TypeScript.** Interop is the moat.
- ✅ **JSONL append-only.** Easy to grep, easy to ship to S3 later if you want.
- ✅ **State snapshots via `dill` (Python) / `superjson` (TypeScript).** Best-effort with clear failure modes.
- ✅ **No accounts. No telemetry. No vendor lock-in.** Period.

[Read the full architecture →](./docs/architecture.md)

## 📦 Installation

### Prerequisites

- **Python 3.10+** (for the Python SDK + dashboard server)
- **Node 20+** (for the TypeScript SDK)
- **A LLM SDK** (anthropic or openai, your choice)

### Python SDK

```bash
pip install branchpoint
```

### TypeScript SDK

```bash
npm install @branchpoint/sdk
# or pnpm add @branchpoint/sdk
```

### Dashboard

The dashboard ships with the Python package. After `pip install branchpoint`:

```bash
branchpoint dashboard
```

That's it. No separate install. Web UI on `http://localhost:3089`.

## 🗺️ Roadmap

We're shipping v0.1 in 6 weekend-sized sessions:

- [x] **Session 1** — Repo scaffolding, schemas, CLAUDE.md
- [ ] **Session 2** — Python SDK Recorder + JSONL storage
- [ ] **Session 3** — TypeScript SDK Recorder (parity)
- [ ] **Session 4** — Auto-instrumentation of Anthropic + OpenAI SDKs
- [ ] **Session 5** — FastAPI backend + Next.js dashboard (observability)
- [ ] **Session 6** — **Branching & replay** (the feature) + demo video + launch

**After v0.1:**
- LangGraph + CrewAI + Pydantic AI integrations
- Evaluation mode (run a branch over a dataset, get win rate)
- VS Code extension
- Optional cloud sync (opt-in, encrypted)

[Follow progress →](./WORK_LOG.md)

## 🤝 Contributing

We're pre-alpha. The biggest help right now:

- 🐛 **Try it and break it.** Run the examples, file issues with reproducible traces.
- 🧩 **Add a framework integration.** LangGraph, CrewAI, OpenAI Agents SDK. ~150 LOC each.
- 📚 **Improve docs.** Especially examples.

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## ⚖️ Known limitations

Be honest about what doesn't work yet:

- 🚧 **Non-deterministic replay.** Re-running with `temperature > 0` gives different results. We can show that comparison faithfully, but we can't promise reproducibility.
- 🚧 **Side effects on replay.** If your step inserted into a database, replaying it would duplicate. Mark side-effecting tools with `@bp.tool(side_effects=True)` to get a confirmation before replay.
- 🚧 **TypeScript snapshots are weaker than Python.** `superjson` doesn't handle closures the way Python's `dill` does. We're working on a manifest-based approach.
- 🚧 **Framework integrations are post-v0.1.** Direct SDK calls (Anthropic, OpenAI) work in v0.1; LangGraph/CrewAI/etc. come after.

## 📜 License

MIT © Ricardo Cuadros and contributors.

## 🙏 Acknowledgments

- Microsoft Research's [AGDebugger paper](https://arxiv.org/abs/2503.02068) (CHI 2025) — academic validation of the counterfactual debugging pattern.
- The OpenTelemetry community for the auto-instrumentation patterns we borrow.
- LangSmith and Langfuse for showing what observability dashboards should look like; we're building the missing time-travel layer.

---

<div align="center">
<sub>Built with ❤️ in Lima, Perú · <a href="https://github.com/ricardomiguelcuadrosrodriguez/branchpoint">github</a></sub>
</div>
