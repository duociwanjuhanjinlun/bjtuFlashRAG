#!/usr/bin/env python
import argparse
from pathlib import Path

from flashrag.config import Config
from flashrag.pipeline import AdaptivePipeline, ConditionalPipeline, SequentialPipeline
from flashrag.utils import get_dataset


PIPELINE_FACTORY = {
    "sequential": SequentialPipeline,
    "conditional": ConditionalPipeline,
    "adaptive": AdaptivePipeline,
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
    parser = argparse.ArgumentParser(description="Run FlashRAG DeepSearch pipeline.")
    parser.add_argument("--config", type=Path, default=Path("configs/deepsearch_adaptive.yaml"))
    parser.add_argument("--pipeline", choices=PIPELINE_FACTORY.keys(), default="adaptive")
    parser.add_argument("--split", default=None, help="Dataset split to evaluate.")
    parser.add_argument("--data-dir", default=None, help="Override data directory at runtime.")
    parser.add_argument("--output-dir", default=None, help="Override save directory at runtime.")
    parser.add_argument("--skip-eval", action="store_true", help="Skip metric computation.")
    parser.add_argument("--sample-num", type=int, default=None, help="Override test_sample_num at runtime.")
    args = parser.parse_args()

    config = build_config(args.config, args.data_dir, args.output_dir)
    if args.sample_num is not None:
        config["test_sample_num"] = args.sample_num
    print(f"Config: {config}")
    dataset = load_dataset(config, args.split)
    print(f"Dataset: {dataset}")
    pipeline_cls = PIPELINE_FACTORY[args.pipeline]
    pipeline = pipeline_cls(config)
    pipeline.run(dataset, do_eval=not args.skip_eval)


if __name__ == "__main__":
    main()

