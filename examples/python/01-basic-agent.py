"""Example: a basic single-call agent traced with branchpoint.

Run:
    pip install branchpoint anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python 01-basic-agent.py
    branchpoint dashboard
"""
import branchpoint as bp
import anthropic


@bp.trace(name="why-is-the-sky-blue")
def explain_sky() -> str:
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[
            {"role": "user", "content": "Why is the sky blue? Answer in 3 sentences."}
        ],
    )
    return response.content[0].text


if __name__ == "__main__":
    answer = explain_sky()
    print(answer)
    print("\nRun `branchpoint dashboard` to see the trace.")
