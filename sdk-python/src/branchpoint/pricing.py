"""LLM pricing tables.

USD per 1M tokens. Maintained manually based on official provider pricing
pages as of May 2026. Update when models or prices change.

Pricing is computed CLIENT-SIDE for cost tracking. We don't proxy or charge
anything. These numbers are best-effort — verify with your billing dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    """USD per 1 million tokens."""
    input_per_1m: float
    output_per_1m: float
    cached_input_per_1m: float | None = None  # for prompt caching


# ---------------------------------------------------------------------------
# Anthropic (May 2026 — verify at https://www.anthropic.com/pricing)
# ---------------------------------------------------------------------------

ANTHROPIC = {
    # Claude 4.x family (verify current pricing)
    "claude-opus-4-7": ModelPricing(15.00, 75.00, 1.50),
    "claude-opus-4-6": ModelPricing(15.00, 75.00, 1.50),
    "claude-sonnet-4-6": ModelPricing(3.00, 15.00, 0.30),
    "claude-haiku-4-5": ModelPricing(0.80, 4.00, 0.08),
    # Older versions still in use
    "claude-3-5-sonnet-20241022": ModelPricing(3.00, 15.00, 0.30),
    "claude-3-5-haiku-20241022": ModelPricing(0.80, 4.00, 0.08),
}

# ---------------------------------------------------------------------------
# OpenAI (May 2026 — verify at https://openai.com/pricing)
# ---------------------------------------------------------------------------

OPENAI = {
    "gpt-4o": ModelPricing(2.50, 10.00, 1.25),
    "gpt-4o-mini": ModelPricing(0.15, 0.60, 0.075),
    "o3": ModelPricing(15.00, 60.00, 7.50),
    "o3-mini": ModelPricing(1.10, 4.40, 0.55),
    "o4-mini": ModelPricing(1.10, 4.40, 0.55),
}


def compute_cost_usd(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> float:
    """Compute cost in USD given a provider, model, and token counts.

    Returns 0.0 for unknown models (we log a warning elsewhere).
    """
    table = {"anthropic": ANTHROPIC, "openai": OPENAI}.get(provider, {})

    # Try exact match first, then fuzzy match (model may include suffixes)
    pricing = table.get(model)
    if pricing is None:
        for known_model, p in table.items():
            if model.startswith(known_model) or known_model.startswith(model):
                pricing = p
                break

    if pricing is None:
        return 0.0

    cost = (input_tokens / 1_000_000) * pricing.input_per_1m
    cost += (output_tokens / 1_000_000) * pricing.output_per_1m

    if cached_tokens and pricing.cached_input_per_1m is not None:
        # Cached tokens replace some of the input cost; we charge cached rate
        # for those and full input rate only for the non-cached.
        # Note: this is simplified; the actual semantics depend on the provider.
        cost += (cached_tokens / 1_000_000) * pricing.cached_input_per_1m

    return round(cost, 6)


def is_known_model(provider: str, model: str) -> bool:
    """Quick check used by tests."""
    table = {"anthropic": ANTHROPIC, "openai": OPENAI}.get(provider, {})
    return model in table or any(
        model.startswith(m) or m.startswith(model) for m in table
    )
