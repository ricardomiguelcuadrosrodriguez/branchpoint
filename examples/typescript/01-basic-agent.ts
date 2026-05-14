/**
 * Example: a basic single-call agent traced with branchpoint.
 *
 * Run:
 *   pnpm install @branchpoint/sdk @anthropic-ai/sdk
 *   export ANTHROPIC_API_KEY=sk-ant-...
 *   tsx 01-basic-agent.ts
 *   branchpoint dashboard
 */
import * as bp from "@branchpoint/sdk";
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const explainSky = bp.trace("why-is-the-sky-blue", async (): Promise<string> => {
  const response = await client.messages.create({
    model: "claude-sonnet-4-6",
    max_tokens: 512,
    messages: [
      { role: "user", content: "Why is the sky blue? Answer in 3 sentences." },
    ],
  });
  const block = response.content[0];
  return block.type === "text" ? block.text : "";
});

const answer = await explainSky();
console.log(answer);
console.log("\nRun `branchpoint dashboard` to see the trace.");
