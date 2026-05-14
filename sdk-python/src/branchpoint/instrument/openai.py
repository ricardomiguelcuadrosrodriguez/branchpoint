"""Auto-instrumentation for the openai Python SDK.

Patches `openai.OpenAI.chat.completions.create()` (and async + responses API)
to emit `llm_call` events to the active session.

Full implementation in Session 4.
"""
from __future__ import annotations


_PATCHED = False


def patch() -> None:
    """Monkey-patch the openai SDK. Idempotent."""
    global _PATCHED
    if _PATCHED:
        return

    # Session 4 will:
    # 1. Import `openai`
    # 2. Wrap `openai.resources.chat.completions.Completions.create`
    # 3. Wrap `openai.resources.responses.Responses.create` (Responses API)
    # 4. Same for async versions
    # 5. Pattern matches anthropic.py
    # 6. Provider is "openai"

    _PATCHED = True


def unpatch() -> None:
    global _PATCHED
    if not _PATCHED:
        return
    _PATCHED = False
