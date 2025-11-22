#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def convert_split(source_path: Path, target_dir: Path, split: str) -> Path:
    with source_path.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{split}.jsonl"

    with target_path.open("w", encoding="utf-8") as f:
        for item in raw_data:
            record = {
                "id": item["id"],
                "question": item["input_field"],
                "golden_answers": [item["output_field"]],
                "metadata": {},
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return target_path


def parse_args():
    parser = argparse.ArgumentParser(description="Convert FlashRAG DeepSearch dataset.")
    parser.add_argument("--source", type=Path, required=True, help="Path to raw json file.")
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path("/data/bjtu_deepsearch/dataset/deepsearch"),
        help="Directory to save converted jsonl split.",
    )
    parser.add_argument(
        "--split",
        default="test",
        help="Dataset split name to use for the converted file.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    written_path = convert_split(args.source, args.target_dir, args.split)
    print(f"Converted dataset saved to {written_path}")


if __name__ == "__main__":
    main()

