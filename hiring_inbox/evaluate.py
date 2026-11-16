"""Score exact primary-intent matches on the Milestone 1 fixture."""

import argparse
import csv
from collections import Counter
from pathlib import Path

from hiring_inbox.classifier import Intent, classify_intent


DATASET = Path(__file__).resolve().parents[1] / "data" / "messages.csv"


def report(split: str, messages: list[dict[str, str]]) -> None:
    counts: Counter[tuple[Intent, Intent]] = Counter()
    misses = []
    for message in messages:
        expected = Intent(message["expected_intent"])
        predicted = classify_intent(message["message_text"])
        counts[expected, predicted] += 1
        if expected != predicted:
            misses.append((message, expected, predicted))

    total = len(messages)
    correct = total - len(misses)
    print(f"{split}: {correct}/{total} correct ({correct / total:.1%})")
    print("Confusion matrix (expected rows, predicted columns)")
    print("expected \\ predicted", *(intent.value for intent in Intent), sep="\t")
    for expected in Intent:
        print(expected.value, *(counts[expected, predicted] for predicted in Intent), sep="\t")

    print("Misclassified examples")
    for message, expected, predicted in misses:
        print(f"- #{message['message_id']}: expected {expected}, predicted {predicted}")
        print(f"  {message['message_text']!r}")
    if not misses:
        print("None")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--split",
        choices=("dev", "holdout", "all"),
        default="dev",
        help="split to score (default: dev for routine use)",
    )
    selection = parser.parse_args().split
    with DATASET.open(encoding="utf-8", newline="") as source:
        messages = list(csv.DictReader(source))

    splits = ("dev", "holdout") if selection == "all" else (selection,)
    for split in splits:
        selected = [message for message in messages if message["split"] == split]
        if not selected:
            parser.error(f"no messages for split {split!r}")
        report(split, selected)
        print()


if __name__ == "__main__":
    main()
