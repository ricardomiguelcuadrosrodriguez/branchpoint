"""Example: a multi-step research agent.

Each function decorated with @bp.trace becomes a nested step in the trace,
so you can branch from ANY of them in the dashboard, not just the top level.

Run:
    pip install branchpoint anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python 02-tool-using-agent.py
"""
import branchpoint as bp
import anthropic


client = anthropic.Anthropic()


@bp.trace(name="research")
def research_agent(topic: str) -> str:
    """Top-level agent. Three nested steps."""
    keywords = extract_keywords(topic)
    summaries = [summarize_keyword(k) for k in keywords]
    return synthesize(topic, summaries)


@bp.trace(name="extract-keywords")
def extract_keywords(topic: str) -> list[str]:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        messages=[
            {
                "role": "user",
                "content": f"List exactly 3 keywords related to: {topic}. "
                f"Reply with ONLY the keywords, one per line.",
            }
        ],
    )
    text = response.content[0].text
    return [line.strip() for line in text.split("\n") if line.strip()][:3]


@bp.trace(name="summarize-keyword")
def summarize_keyword(keyword: str) -> str:
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        messages=[
            {"role": "user", "content": f"In 2 sentences, explain: {keyword}"}
        ],
    )
    return response.content[0].text


@bp.trace(name="synthesize")
def synthesize(topic: str, summaries: list[str]) -> str:
    combined = "\n".join(f"- {s}" for s in summaries)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Topic: {topic}\n\n"
                    f"Key findings:\n{combined}\n\n"
                    f"Synthesize these into a coherent 1-paragraph summary."
                ),
            }
        ],
    )
    return response.content[0].text


if __name__ == "__main__":
    result = research_agent("Quantum computing in 2026")
    print(result)
    print("\nRun `branchpoint dashboard` to see the trace.")
