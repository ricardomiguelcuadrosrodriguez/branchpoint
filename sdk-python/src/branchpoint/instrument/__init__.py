"""Auto-instrumentation of LLM SDKs.

When a `Recorder` is active, calls to the patched SDKs emit `llm_call`
events automatically — no code changes in user agent code.

Each submodule patches one provider. Patches are applied lazily on first
import of branchpoint (in `__init__.py` via `install_patches()`).

Full implementations land in Session 4 (see WORK_LOG.md).
"""
from __future__ import annotations


def install_patches() -> None:
    """Apply all available patches. Safe to call multiple times."""
    try:
        from branchpoint.instrument import anthropic as _anthropic
        _anthropic.patch()
    except ImportError:
        pass  # anthropic SDK not installed; user doesn't need it

    try:
        from branchpoint.instrument import openai as _openai
        _openai.patch()
    except ImportError:
        pass  # openai SDK not installed; user doesn't need it
