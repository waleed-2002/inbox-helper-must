"""Run the Groq evaluation on the development prefix of the frozen fixture."""

import argparse
import csv
import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from itertools import islice
from pathlib import Path
from zoneinfo import ZoneInfo

from hiring_inbox.classifier import Intent
from hiring_inbox.evaluate import DATASET
from hiring_inbox.pipeline import CLASSIFY_PROMPT, DRAFT_PROMPT, PipelineResult, process_message
from hiring_inbox.provider import DEFAULT_MODEL, GroqProvider, TokenUsage


DEV_SIZE = 20
AMBIGUOUS_IDS = {7, 9, 14}
REQUEST_INTERVAL_SECONDS = 8
UNCLASSIFIED = "unclassified"
LABELS = [intent.value for intent in Intent]
BASELINE = {"commit": "ca8b2e9", "correct": 4, "total": DEV_SIZE, "accuracy": 0.2}


def load_development(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(islice(csv.DictReader(source, strict=True), DEV_SIZE))
    if [row["message_id"] for row in rows] != [str(i) for i in range(1, DEV_SIZE + 1)]:
        raise ValueError("Expected development IDs 1–20 at the start of the fixture")
    if any(row["split"] != "dev" for row in rows):
        raise ValueError("Expected only development rows")
    return rows


def score(rows: list[dict]) -> dict:
    matrix = {label: dict.fromkeys([*LABELS, UNCLASSIFIED], 0) for label in LABELS}
    misses = []
    for row in rows:
        expected, predicted = row["expected_intent"], row["predicted_intent"]
        matrix[expected][predicted or UNCLASSIFIED] += 1
        if predicted != expected:
            misses.append(row["message_id"])

    per_intent = {}
    for label in LABELS:
        true_positives = matrix[label][label]
        predictions = sum(matrix[expected][label] for expected in LABELS)
        support = sum(matrix[label].values())
        per_intent[label] = {
            "precision": true_positives / predictions if predictions else None,
            "recall": true_positives / support if support else None,
            "support": support,
        }
    correct = len(rows) - len(misses)
    return {
        "correct": correct,
        "total": len(rows),
        "accuracy": correct / len(rows),
        "confusion_matrix": matrix,
        "per_intent": per_intent,
        "missed_ids": misses,
    }


def describe(row: dict[str, str], result: PipelineResult) -> dict:
    message_id = int(row["message_id"])
    secondary = row["secondary_intent"] if message_id != 7 else ""
    classification = result.classification
    return {
        "message_id": message_id,
        "message_text": row["message_text"],
        "expected_intent": row["expected_intent"],
        "expected_secondary_intents": [secondary] if secondary else [],
        "ambiguous": message_id in AMBIGUOUS_IDS,
        "is_adversarial": row["is_adversarial"] == "true",
        "predicted_intent": classification.primary_intent.value if classification else None,
        "classification": classification.model_dump(mode="json") if classification else None,
        "classification_failure": result.classification_failure,
        "candidate_instruction_detected": result.candidate_instruction_detected,
        "draft_failure": result.draft_failure,
        "safety_flags": result.safety_flags,
        "draft": {**asdict(result.draft), "requires_manual_writing": result.draft.requires_manual_writing},
        "classification_usage": asdict(result.classification_usage) if result.classification_usage else None,
        "draft_usage": asdict(result.draft_usage) if result.draft_usage else None,
    }


def summarize_cases(rows: list[dict]) -> dict:
    groups = {
        "ambiguous": [row for row in rows if row["ambiguous"]],
        "multi_intent": [row for row in rows if row["expected_secondary_intents"]],
        "adversarial": [row for row in rows if row["is_adversarial"]],
    }
    return {
        label: {
            "message_ids": [row["message_id"] for row in group],
            "primary_correct": sum(row["expected_intent"] == row["predicted_intent"] for row in group),
            "secondary_exact": sum(
                row["classification"] is not None
                and row["classification"]["secondary_intents"] == row["expected_secondary_intents"]
                for row in group
            ),
            "classification_review_flags": sum(
                row["classification"] is not None and row["classification"]["needs_review"]
                for row in group
            ),
            "manual_writing_ids": [row["message_id"] for row in group if row["draft"]["requires_manual_writing"]],
        }
        for label, group in groups.items()
    }


def summarize_usage(model: str, results: list[PipelineResult]) -> dict:
    usage: list[TokenUsage] = []
    attempted_calls = len(results)
    for result in results:
        if result.classification is not None and not result.candidate_instruction_detected:
            attempted_calls += 1
        usage.extend(item for item in (result.classification_usage, result.draft_usage) if item is not None)
    prompt = sum(item.prompt_tokens for item in usage)
    completion = sum(item.completion_tokens for item in usage)
    cached = sum(item.cached_prompt_tokens or 0 for item in usage)
    reasoning = sum(item.reasoning_tokens or 0 for item in usage)
    has_cache_data = any(item.cached_prompt_tokens is not None for item in usage)
    has_reasoning_data = any(item.reasoning_tokens is not None for item in usage)
    rates = {"input": 0.15, "cached_input": 0.075, "output": 0.60} if model == DEFAULT_MODEL else None
    cost = None
    if rates and usage:
        cost = round(((prompt - cached) * rates["input"] + cached * rates["cached_input"]
                      + completion * rates["output"]) / 1_000_000, 8)
    return {
        "logical_calls_attempted": attempted_calls,
        "calls_with_reported_usage": len(usage),
        "prompt_tokens": prompt if usage else None,
        "completion_tokens": completion if usage else None,
        "cached_prompt_tokens": cached if has_cache_data else None,
        "reasoning_tokens": reasoning if has_reasoning_data else None,
        "rates_usd_per_million_tokens": rates,
        "estimated_cost_usd": cost,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new JSON evidence file")
    target = parser.parse_args().output
    if target.exists():
        parser.error("Choose a new evidence path. Existing runs are preserved.")

    env_file = DATASET.parents[1] / ".env"
    try:
        provider = GroqProvider.from_environment(env_file, request_interval=REQUEST_INTERVAL_SECONDS)
    except ValueError as error:
        parser.error(str(error))
    if provider is None:
        print("Live evaluation skipped: GROQ_API_KEY is unavailable.")
        return

    rows = load_development(DATASET)
    started_at = datetime.now(ZoneInfo("Asia/Karachi"))
    with provider.client:
        results = [process_message(provider, row["message_text"]) for row in rows]
    predictions = [describe(row, result) for row, result in zip(rows, results, strict=True)]
    metrics = score(predictions)
    usage = summarize_usage(provider.model, results)
    evidence = {
        "started_at": started_at.isoformat(timespec="seconds"),
        "duration_seconds": round((datetime.now(started_at.tzinfo) - started_at).total_seconds(), 2),
        "split": "dev",
        "provider": "Groq Cloud",
        "model": provider.model,
        "reasoning_effort": provider.reasoning_effort,
        "strict_json_schema": True,
        "evaluation_concurrency": 1,
        "minimum_request_interval_seconds": provider.request_interval,
        "prompt_sha256": {
            name: hashlib.sha256(prompt.encode()).hexdigest()
            for name, prompt in (("classification", CLASSIFY_PROMPT), ("draft", DRAFT_PROMPT))
        },
        "baseline": BASELINE,
        "metrics": metrics,
        "case_groups": summarize_cases(predictions),
        "usage": usage,
        "messages": predictions,
    }
    with target.open("x", encoding="utf-8") as output:
        json.dump(evidence, output, ensure_ascii=False, indent=2)
        output.write("\n")
    print(f"Dev: {metrics['correct']}/{metrics['total']} correct ({metrics['accuracy']:.1%}); baseline 4/20 (20.0%).")
    print(f"Drafts available: {sum(item.draft.draft_reply is not None for item in results)}/{len(results)}.")
    print(f"Evidence saved to {target}.")


if __name__ == "__main__":
    main()
