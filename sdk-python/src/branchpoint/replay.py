"""Branch + replay engine.

Given an existing session and a step to branch from, plus optional
modifications (different prompt, different model, etc.), this module
re-executes the agent from that step onwards, writing a new session
linked to the original.

This is THE feature of branchpoint. Full implementation in Session 6.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class BranchSpec:
    """User's instructions for how to branch.

    Example:
        BranchSpec(
            from_session="01HK...",
            from_step="step-003",
            modifications={
                "llm_call.request.messages[0].content": "New prompt text",
                "llm_call.model": "claude-opus-4-7",
            },
        )
    """

    def __init__(
        self,
        from_session: str,
        from_step: str,
        modifications: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> None:
        self.from_session = from_session
        self.from_step = from_step
        self.modifications = modifications or {}
        self.name = name


def branch_from(spec: BranchSpec) -> str:
    """Execute a branch and return the new session_id.

    High-level algorithm (Session 6):
        1. Load original session's trace.jsonl
        2. Find step `from_step`
        3. Load the state snapshot from step (from_step - 1)
        4. Open a new Recorder with parent_session_id + parent_step_id set
        5. Replay deterministic events up to from_step
        6. For from_step, apply user modifications
        7. Resume normal execution from from_step + 1
        8. Write new trace to new session dir
        9. Return new session_id

    Caveats:
        - Tools marked side_effects=True will pause for confirmation
        - Non-deterministic LLM responses may diverge after from_step (expected)
        - If a snapshot can't be restored (closure broke), fail loudly
    """
    raise NotImplementedError("Session 6")
