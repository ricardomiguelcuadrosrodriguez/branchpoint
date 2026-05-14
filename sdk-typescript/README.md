# @branchpoint/sdk (TypeScript SDK)

The TypeScript SDK for [branchpoint](https://github.com/ricardomiguelcuadrosrodriguez/branchpoint) — a time-travel debugger for AI agents.

## Install

```bash
npm install @branchpoint/sdk
# or
pnpm add @branchpoint/sdk
```

You'll typically also want one of:

```bash
npm install @anthropic-ai/sdk    # auto-instrumented
npm install openai               # auto-instrumented
```

## Quickstart

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

// Open the dashboard:
// $ branchpoint dashboard
```

## API

### `bp.trace(name, fn, options?)`

Wrap an async function so it participates in recording.

### `bp.tool({ name, sideEffects }, fn)`

Wrap a function as a tool. Mark `sideEffects: true` for tools that write to external systems.

### `bp.record(options, asyncFn)`

Explicit session control:

```typescript
await bp.record({ name: "my-agent" }, async (session) => {
  // ... your code ...
  console.log(`Cost: $${session.costUsd}`);
});
```

## Why wrappers, not decorators?

TC39 decorators are still settling in 2026. Wrapper functions like `bp.trace(name, fn)` work in every JS runtime (Node, Bun, Deno) without flags, so we prefer them.

## Development

```bash
cd sdk-typescript
pnpm install
pnpm test
pnpm build
```

## License

MIT
