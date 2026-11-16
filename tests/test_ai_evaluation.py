from io import StringIO

import pytest

from hiring_inbox.evaluate_ai import load_development, score, summarize_usage
from hiring_inbox.pipeline import PipelineResult
from hiring_inbox.provider import DEFAULT_MODEL, GroqProvider, TokenUsage
from hiring_inbox.schemas import ReviewDraft


def test_development_loader_stops_at_row_twenty():
    class DevOnlySource(StringIO):
        def __next__(self):
            try:
                return super().__next__()
            except StopIteration:
                pytest.fail("The development loader read past the final development record")

    class FixturePath:
        def open(self, **kwargs):
            lines = ["message_id,split", *(f"{number},dev" for number in range(1, 21))]
            return DevOnlySource("\n".join(lines) + "\n")

    rows = load_development(FixturePath())
    assert len(rows) == 20 and rows[-1]["message_id"] == "20"


def test_missing_credentials_returns_no_provider(monkeypatch, tmp_path):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert GroqProvider.from_environment(tmp_path / ".env") is None


def test_evaluation_counts_unclassified_as_a_miss():
    metrics = score([
        {"message_id": 1, "expected_intent": "withdrawal", "predicted_intent": "withdrawal"},
        {"message_id": 2, "expected_intent": "withdrawal", "predicted_intent": None},
        {"message_id": 3, "expected_intent": "other", "predicted_intent": "withdrawal"},
    ])
    assert metrics["accuracy"] == pytest.approx(1 / 3)
    assert metrics["missed_ids"] == [2, 3]
    assert metrics["confusion_matrix"]["withdrawal"]["unclassified"] == 1
    assert metrics["per_intent"]["withdrawal"] == {"precision": 0.5, "recall": 0.5, "support": 2}
    assert metrics["per_intent"]["other"]["precision"] is None


def test_usage_counts_cached_tokens_and_does_not_double_count_reasoning():
    result = PipelineResult(
        classification=None,
        draft=ReviewDraft(None, "Manual writing required."),
        classification_usage=TokenUsage(1_000, 500, cached_prompt_tokens=200, reasoning_tokens=300),
    )
    usage = summarize_usage(DEFAULT_MODEL, [result])
    assert usage["calls_with_reported_usage"] == usage["logical_calls_attempted"] == 1
    assert usage["completion_tokens"] == 500
    assert usage["estimated_cost_usd"] == pytest.approx(0.000435)
