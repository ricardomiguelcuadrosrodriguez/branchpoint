"""Auto-instrumentation for the anthropic Python SDK.

Patches `anthropic.Anthropic.messages.create()` (and the async equivalent)
to emit `llm_call` events to the active session.

Full implementation in Session 4. This stub documents the patching strategy
so it's clear what needs to happen.
"""
from __future__ import annotations


_PATCHED = False


def patch() -> None:
    """Monkey-patch the anthropic SDK. Idempotent."""
    global _PATCHED
    if _PATCHED:
        return

    # Session 4 will:
    # 1. Import `anthropic`
    # 2. Wrap `anthropic.resources.messages.Messages.create`
    # 3. Same for `anthropic.resources.messages.AsyncMessages.create`
    # 4. On each call:
    #    - Get the active Recorder from contextvars
    #    - If no active recorder, pass through unchanged
    #    - If active:
    #      - Record timestamp + duration
    #      - Capture request kwargs verbatim
    #      - Run the real call
    #      - Capture response
    #      - Compute cost from pricing table (usage tokens + model)
    #      - Emit LLMCallEvent
    #    - Return original response

    _PATCHED = True


def unpatch() -> None:
    """Restore the original anthropic SDK. Useful in tests."""
    global _PATCHED
    if not _PATCHED:
        return
    # Session 4: restore the originals.
    _PATCHED = False
