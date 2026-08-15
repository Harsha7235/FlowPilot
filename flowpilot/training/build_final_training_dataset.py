from __future__ import annotations

import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

V4_DIR = ROOT / "flowpilot" / "training" / "dataset_v4"
SOURCE_DIR = ROOT / "flowpilot" / "training" / "source_code_dataset_v2"

OUTPUT_DIR = (
    ROOT
    / "flowpilot"
    / "training"
    / "final_training"
)

SEED = 42


def load_jsonl(path: Path) -> list[dict]:
    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(
                    json.loads(line)
                )
            except json.JSONDecodeError:
                continue

    return records


def clean_text(value) -> str:
    if value is None:
        return ""

    return str(value).strip()


def convert_record(
    record: dict,
) -> dict | None:

    instruction = clean_text(
        record.get("instruction")
    )

    context = clean_text(
        record.get("context")
    )

    response = clean_text(
        record.get("response")
    )

    if not instruction or not response:
        return None

    # Keep context separate so the model learns
    # that retrieved technical information is evidence.
    if context:

        user_content = (
            "Context:\n"
            + context
            + "\n\n"
            "Question:\n"
            + instruction
        )

    else:

        user_content = instruction

    metadata = record.get(
        "metadata",
        {},
    )

    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are FlowPilot, a specialized "
                    "GNU Radio and SDR engineering "
                    "assistant. Answer using the "
                    "provided technical context. "
                    "Be precise, direct, and concise. "
                    "Do not invent implementation "
                    "details that are not supported "
                    "by the context."
                ),
            },
            {
                "role": "user",
                "content": user_content,
            },
            {
                "role": "assistant",
                "content": response,
            },
        ],
        "metadata": {
            "source": metadata.get(
                "source",
                "unknown",
            ),
            "type": metadata.get(
                "type",
                "unknown",
            ),
        },
    }


def deduplicate(
    records: list[dict],
) -> list[dict]:

    seen = set()
    result = []

    for record in records:

        messages = record.get(
            "messages",
            [],
        )

        if len(messages) != 3:
            continue

        user = messages[1].get(
            "content",
            "",
        )

        assistant = messages[2].get(
            "content",
            "",
        )

        key = (
            user.strip().lower(),
            assistant.strip().lower(),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(record)

    return result


def process_split(
    split: str,
) -> tuple[list[dict], dict]:

    v4_path = (
        V4_DIR / f"{split}.jsonl"
    )

    source_path = (
        SOURCE_DIR / f"{split}.jsonl"
    )

    v4_records = load_jsonl(
        v4_path
    )

    source_records = load_jsonl(
        source_path
    )

    converted = []

    for record in (
        v4_records
        + source_records
    ):

        converted_record = convert_record(
            record
        )

        if converted_record is not None:
            converted.append(
                converted_record
            )

    before = len(
        converted
    )

    converted = deduplicate(
        converted
    )

    after = len(
        converted
    )

    stats = {
        "v4": len(v4_records),
        "source_v2": len(source_records),
        "combined": before,
        "after_deduplication": after,
    }

    return converted, stats


def write_jsonl(
    path: Path,
    records: list[dict],
) -> None:

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        for record in records:

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )


def main() -> None:

    random.seed(
        SEED
    )

    print()
    print(
        "========================================"
    )
    print(
        "FLOWPILOT FINAL TRAINING DATASET"
    )
    print(
        "========================================"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_stats = {}

    for split in (
        "train",
        "validation",
        "test",
    ):

        print()
        print(
            f"[{split.upper()}]"
        )

        records, stats = process_split(
            split
        )

        random.shuffle(
            records
        )

        write_jsonl(
            OUTPUT_DIR
            / f"{split}.jsonl",
            records,
        )

        all_stats[split] = stats

        print(
            "V4:",
            stats["v4"],
        )

        print(
            "Source V2:",
            stats["source_v2"],
        )

        print(
            "Combined:",
            stats["combined"],
        )

        print(
            "After dedup:",
            stats["after_deduplication"],
        )

    manifest = {
        "name": "FlowPilot Final Training Dataset",
        "version": "1.0",
        "seed": SEED,
        "sources": {
            "knowledge_v4": str(
                V4_DIR
            ),
            "source_code_v2": str(
                SOURCE_DIR
            ),
        },
        "splits": all_stats,
    }

    (
        OUTPUT_DIR / "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        "========================================"
    )
    print(
        "FINAL DATASET COMPLETE"
    )
    print(
        "========================================"
    )

    for split in (
        "train",
        "validation",
        "test",
    ):

        print(
            f"{split}:",
            all_stats[split][
                "after_deduplication"
            ],
        )

    print()
    print(
        "Output:"
    )

    print(
        OUTPUT_DIR
    )


if __name__ == "__main__":
    main()