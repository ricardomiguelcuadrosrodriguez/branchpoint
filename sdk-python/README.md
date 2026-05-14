# branchpoint (Python SDK)

The Python SDK for [branchpoint](https://github.com/ricardomiguelcuadrosrodriguez/branchpoint) — a time-travel debugger for AI agents.

## Install

```bash
pip install branchpoint
```

Optional extras:

```bash
pip install "branchpoint[anthropic]"   # auto-instrument anthropic SDK
pip install "branchpoint[openai]"      # auto-instrument openai SDK
pip install "branchpoint[server]"      # include the dashboard server
pip install "branchpoint[all]"         # everything
```

## Quickstart

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

## API

### `@bp.trace(name, tags)`

Decorate a function as a top-level traced agent.

### `@bp.tool(name, side_effects)`

Decorate a function as a tool. Mark `side_effects=True` for tools that write to external systems (DBs, APIs) so they pause for confirmation on replay.

### `bp.record(name, tags)` context manager

Explicit session control:

```python
with bp.record(name="my-agent") as session:
    # ... your code ...
    print(f"Cost so far: ${session.cost_usd:.4f}")
```

## Development

```bash
cd sdk-python
python -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"
pytest
```

## License

MIT
