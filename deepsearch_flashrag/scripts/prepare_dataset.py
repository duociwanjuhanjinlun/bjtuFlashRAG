#!/usr/bin/env python
import argparse
import json
from pathlib import Path


def convert_split(source_path: Path, target_dir: Path, split: str, has_answers: bool = True) -> Path:
    """
    将原始 JSON 数据转换为 FlashRAG 格式的 jsonl
    
    Args:
        source_path: 输入的 JSON 文件路径
        target_dir: 输出目录
        split: 数据集分割名称（如 "test", "dev"）
        has_answers: 是否包含正确答案（如果有 output_field 则为 True，否则为 False）
    """
    with source_path.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{split}.jsonl"

    with target_path.open("w", encoding="utf-8") as f:
        for item in raw_data:
            record = {
                "id": item["id"],
                "question": item["input_field"],
                "metadata": {},
            }
            
            # 如果有正确答案，添加 golden_answers
            if has_answers and "output_field" in item:
                record["golden_answers"] = [item["output_field"]]
            else:
                # 如果没有正确答案，使用空列表（测试集）
                record["golden_answers"] = []
            
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
    parser.add_argument(
        "--no-answers",
        action="store_true",
        help="数据集没有正确答案（测试集），不包含 output_field",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    has_answers = not args.no_answers  # 如果指定了 --no-answers，则 has_answers=False
    written_path = convert_split(args.source, args.target_dir, args.split, has_answers=has_answers)
    print(f"Converted dataset saved to {written_path}")
    print(f"  Has answers: {has_answers}")


if __name__ == "__main__":
    main()

