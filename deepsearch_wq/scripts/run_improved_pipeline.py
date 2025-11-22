#!/usr/bin/env python
"""
运行改进后的DeepSearch Pipeline
支持多种pipeline类型和自定义prompt
"""
import argparse
import sys
from pathlib import Path

# 将项目根目录的父目录添加到 Python 路径，以便导入 deepsearch_flashrag 模块
script_file = Path(__file__).resolve()
script_dir = script_file.parent
project_root = script_dir.parent
parent_dir = project_root.parent  # /root 目录
parent_dir_str = str(parent_dir.resolve())
if parent_dir_str not in sys.path:
    sys.path.insert(0, parent_dir_str)

from flashrag.config import Config
from flashrag.pipeline import (
    AdaptivePipeline, 
    ConditionalPipeline, 
    SequentialPipeline,
    IRCOTPipeline  # 多轮检索pipeline
)
from flashrag.utils import get_dataset
from deepsearch_flashrag.prompts.deepsearch_prompt import DeepSearchPromptTemplate
from deepsearch_flashrag.prompts.ircot_improved_prompt import ImprovedIRCOTPromptTemplate
from deepsearch_flashrag.prompts.ircot_concise_prompt import ConciseIRCOTPromptTemplate


PIPELINE_FACTORY = {
    "sequential": SequentialPipeline,
    "conditional": ConditionalPipeline,
    "adaptive": AdaptivePipeline,
    "ircot": IRCOTPipeline,  # 多轮检索推理pipeline
}


def build_config(config_path: Path, data_dir: str | None = None, output_dir: str | None = None) -> Config:
    overrides = {}
    if data_dir:
        overrides["data_dir"] = data_dir
    if output_dir:
        overrides["save_dir"] = output_dir
    return Config(config_file_path=str(config_path), config_dict=overrides)


def load_dataset(config: Config, split: str | None = None):
    dataset_splits = get_dataset(config)
    target_split = split or config["split"][0]
    if target_split not in dataset_splits:
        raise ValueError(f"Split '{target_split}' not found in dataset folder.")
    dataset = dataset_splits[target_split]
    return dataset


def main():
    parser = argparse.ArgumentParser(description="Run improved FlashRAG DeepSearch pipeline.")
    parser.add_argument("--config", type=Path, default=Path("configs/deepsearch_improved.yaml"))
    parser.add_argument("--pipeline", choices=PIPELINE_FACTORY.keys(), default="ircot",
                        help="Pipeline type: sequential, conditional, adaptive, or ircot (recommended for complex questions)")
    parser.add_argument("--split", default=None, help="Dataset split to evaluate.")
    parser.add_argument("--data-dir", default=None, help="Override data directory at runtime.")
    parser.add_argument("--output-dir", default=None, help="Override save directory at runtime.")
    parser.add_argument("--skip-eval", action="store_true", help="Skip metric computation.")
    parser.add_argument("--sample-num", type=int, default=None, help="Override test_sample_num at runtime.")
    parser.add_argument("--use-custom-prompt", action="store_true", 
                        help="Use optimized DeepSearch prompt template")
    args = parser.parse_args()

    config = build_config(args.config, args.data_dir, args.output_dir)
    if args.sample_num is not None:
        config["test_sample_num"] = args.sample_num
    
    dataset = load_dataset(config, args.split)
    print(f"Loaded {len(dataset)} samples from {args.split} split")
    
    # 创建pipeline
    pipeline_cls = PIPELINE_FACTORY[args.pipeline]
    
    # 使用自定义prompt模板
    if args.use_custom_prompt:
        if args.pipeline == "ircot":
            # IRCoT使用专门的简洁prompt（强调最终答案格式）
            prompt_template = ConciseIRCOTPromptTemplate(config)
            print("Using concise IRCoT prompt template (emphasizes final answer format)")
        else:
            prompt_template = DeepSearchPromptTemplate(config)
            print("Using optimized DeepSearch prompt template")
    else:
        prompt_template = None
        print("Using default prompt template")
    
    # 对于IRCoT pipeline，需要特殊处理
    if args.pipeline == "ircot":
        pipeline = pipeline_cls(config, prompt_template=prompt_template, max_iter=3)
    else:
        pipeline = pipeline_cls(config, prompt_template=prompt_template)
    
    print(f"Running {args.pipeline} pipeline...")
    result = pipeline.run(dataset, do_eval=not args.skip_eval)
    
    print(f"\nResults saved to: {config['save_dir']}")
    return result


if __name__ == "__main__":
    main()

