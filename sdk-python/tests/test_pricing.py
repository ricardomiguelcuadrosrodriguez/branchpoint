"""Tests for the pricing module."""
import pytest

from branchpoint.pricing import (
    ANTHROPIC,
    OPENAI,
    compute_cost_usd,
    is_known_model,
)


class TestComputeCostUsd:
    def test_known_anthropic_model(self) -> None:
        # claude-haiku-4-5: $0.80 input, $4.00 output per 1M tokens
        # 1000 input + 500 output → 0.001*0.80 + 0.0005*4.00 = $0.0028
        cost = compute_cost_usd("anthropic", "claude-haiku-4-5", 1000, 500)
        assert cost == pytest.approx(0.0028, abs=1e-6)

    def test_known_openai_model(self) -> None:
        # gpt-4o-mini: $0.15 input, $0.60 output per 1M tokens
        cost = compute_cost_usd("openai", "gpt-4o-mini", 1000, 500)
        assert cost == pytest.approx(0.00045, abs=1e-6)

    def test_unknown_model_returns_zero(self) -> None:
        cost = compute_cost_usd("anthropic", "nonsense-model", 1000, 500)
        assert cost == 0.0

    def test_unknown_provider_returns_zero(self) -> None:
        cost = compute_cost_usd("xyz", "anything", 1000, 500)
        assert cost == 0.0

    def test_cached_tokens_added(self) -> None:
        # With cached_input_per_1m=0.08 for claude-haiku-4-5
        cost_no_cache = compute_cost_usd("anthropic", "claude-haiku-4-5", 1000, 500, 0)
        cost_with_cache = compute_cost_usd("anthropic", "claude-haiku-4-5", 1000, 500, 500)
        assert cost_with_cache > cost_no_cache


class TestIsKnownModel:
    def test_known_anthropic(self) -> None:
        assert is_known_model("anthropic", "claude-sonnet-4-6")

    def test_known_openai(self) -> None:
        assert is_known_model("openai", "gpt-4o")

    def test_unknown(self) -> None:
        assert not is_known_model("anthropic", "fake-model-9000")


class TestPricingTables:
    def test_anthropic_has_4x_family(self) -> None:
        assert "claude-opus-4-7" in ANTHROPIC
        assert "claude-sonnet-4-6" in ANTHROPIC
        assert "claude-haiku-4-5" in ANTHROPIC

    def test_openai_has_modern_models(self) -> None:
        assert "gpt-4o" in OPENAI
        assert "o3" in OPENAI

    def test_input_cheaper_than_output(self) -> None:
        """Sanity check: input tokens are always cheaper than output."""
        for model, pricing in {**ANTHROPIC, **OPENAI}.items():
            assert pricing.input_per_1m < pricing.output_per_1m, (
                f"{model}: input ({pricing.input_per_1m}) >= "
                f"output ({pricing.output_per_1m})"
            )
