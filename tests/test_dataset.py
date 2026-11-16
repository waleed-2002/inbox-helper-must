import csv

import pytest

from hiring_inbox.classifier import Intent
from hiring_inbox.evaluate import DATASET


@pytest.fixture(scope="module")
def dataset() -> list[dict[str, str]]:
    with DATASET.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        assert reader.fieldnames == [
            "message_id",
            "candidate_name",
            "message_text",
            "expected_intent",
            "secondary_intent",
            "is_adversarial",
            "split",
        ]
        rows = list(reader)
    assert all(None not in row and None not in row.values() for row in rows)
    return rows


def test_dataset_ids_and_splits(dataset: list[dict[str, str]]) -> None:
    assert [row["message_id"] for row in dataset] == [str(number) for number in range(1, 31)]
    assert [row["split"] for row in dataset] == ["dev"] * 20 + ["holdout"] * 10


def test_dataset_content_and_labels(dataset: list[dict[str, str]]) -> None:
    valid_labels = {intent.value for intent in Intent}
    for row in dataset:
        assert row["candidate_name"].strip(), row["message_id"]
        assert row["message_text"].strip(), row["message_id"]
        assert row["expected_intent"] in valid_labels, row["message_id"]
        assert row["secondary_intent"] in valid_labels | {""}, row["message_id"]
        assert row["secondary_intent"] != row["expected_intent"], row["message_id"]
        assert row["is_adversarial"] in {"true", "false"}, row["message_id"]
    assert len({row["message_text"] for row in dataset}) == len(dataset)


@pytest.mark.parametrize("split", ["dev", "holdout"])
def test_dataset_split_coverage(dataset: list[dict[str, str]], split: str) -> None:
    rows = [row for row in dataset if row["split"] == split]
    assert {row["expected_intent"] for row in rows} == {intent.value for intent in Intent}
    assert {row["is_adversarial"] for row in rows} == {"true", "false"}
    assert any(row["secondary_intent"] for row in rows)
