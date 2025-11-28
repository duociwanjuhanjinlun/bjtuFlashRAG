#!/usr/bin/env python
"""
将 intermediate_data.json 转换为提交格式的脚本
从 output.pred 字段提取答案，转换为与提交示例.jsonl一致的格式
"""
import argparse
import json
from pathlib import Path


def convert_intermediate_to_submission(intermediate_path: Path, output_path: Path):
    """
    将 intermediate_data.json 转换为提交格式
    
    Args:
        intermediate_path: intermediate_data.json 的路径
        output_path: 输出的 jsonl 文件路径
    """
    # 读取中间结果
    with intermediate_path.open("r", encoding="utf-8") as f:
        intermediate_data = json.load(f)
    
    # 转换为提交格式
    submission_records = []
    for item in intermediate_data:
        # 提取 id
        record_id = item.get("id", "")
        
        # 提取 pred（答案）
        pred = ""
        if "output" in item and isinstance(item["output"], dict):
            pred = item["output"].get("pred", "")
        
        # 如果 pred 为空或无效，使用默认值
        if not pred or pred.strip() == "":
            pred = "No valid answer found"
        
        # 构建提交记录
        record = {
            "id": record_id,
            "output_field": pred.strip()
        }
        submission_records.append(record)
    
    # 写入 jsonl 文件
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in submission_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"转换完成！")
    print(f"  输入文件: {intermediate_path}")
    print(f"  输出文件: {output_path}")
    print(f"  共转换 {len(submission_records)} 条记录")
    
    # 显示前几条记录作为示例
    if submission_records:
        print(f"\n前 3 条记录示例:")
        for i, record in enumerate(submission_records[:3], 1):
            print(f"  {i}. id={record['id']}, output_field={record['output_field'][:50]}...")


def parse_args():
    parser = argparse.ArgumentParser(
        description="将 intermediate_data.json 转换为提交格式的 jsonl 文件"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("/root/intermediate_data.json"),
        help="输入的 intermediate_data.json 文件路径（默认: /root/intermediate_data.json）"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/root/submission.jsonl"),
        help="输出的 jsonl 文件路径（默认: /root/submission.jsonl）"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    
    # 检查输入文件是否存在
    if not args.input.exists():
        print(f"错误: 输入文件不存在: {args.input}")
        return
    
    # 执行转换
    convert_intermediate_to_submission(args.input, args.output)


if __name__ == "__main__":
    main()

