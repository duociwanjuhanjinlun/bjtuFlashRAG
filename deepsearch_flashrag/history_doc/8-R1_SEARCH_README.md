# DeepSearch R1 Pipeline Upgrade

本文档说明了基于 `DeepSearch` 项目集成的 `R1Search` Pipeline 和 `Selective Context` Refiner 的更新内容。

## 1. 核心改动

### Pipeline 更新: `SearchR1Pipeline`
我们引入了 `FlashRAG` 中的 `SearchR1Pipeline`（位于 `FlashRAG/flashrag/pipeline/reasoning_pipeline.py`）。
- **特点**: 模仿 DeepSeek-R1 的推理模式，模型在 `<think>` 标签内进行推理，并可自主调用 `<search>` 进行多轮检索。
- **优势**: 相比于固定的 IRCoT 流程，R1 模式允许模型更灵活地决定何时搜索、何时停止，适合复杂推理任务。

### Refiner 更新: `Selective Context`
针对复杂推理 QA 任务，我们选择了 `Selective Context` 作为 Refiner。
- **选择理由**: 
    - 复杂推理任务（Reasoning QA）对上下文的逻辑连贯性要求较高。
    - `LLMLingua` 虽然强大但计算开销大且依赖较多。
    - `Selective Context` 基于自信息（Self-Information/Entropy）进行压缩，能够有效去除冗余信息（低惊奇度内容），同时保留高信息量的关键词和短语，且计算速度较快，适合在多轮搜索中反复调用。
- **配置**: 使用 `gpt2` 作为基础模型计算 PPL，压缩率设置为 20% (`reduce_ratio: 0.2`)，以避免过度压缩丢失关键细节。

## 2. 新增文件

- **配置文件**: `@deepsearch_flashrag/configs/r1_search_v1.yaml`
    - 基于 `wq_v6.yaml` 修改。
    - 启用了 `use_refiner: True`。
    - 调整了 `generation_params`，增加了 `max_tokens` (2048) 以支持长思维链。
    - 减少了 `rerank_topk` 到 10，配合 Refiner 进一步精简输入。

- **运行脚本**: `@deepsearch_flashrag/scripts/run_r1_search.py`
    - 实现了 `RefinedSearchR1Pipeline` 类，继承自 `SearchR1Pipeline`。
    - 重写了 `_retrieved_docs_to_string` 方法，在拼接文档前调用 Refiner 对 `text` 进行压缩。

## 3. 如何运行

在 `deepsearch_flashrag` 目录下执行：

```bash
python scripts/run_r1_search.py \
    --config configs/r1_search_v1.yaml \
    --split test \
    --sample-num 20
```

## 4. 参数微调建议

如果发现推理效果不佳，建议调整以下参数：
1. **Refiner 压缩率 (`reduce_ratio`)**: 目前为 0.2。如果模型回答遗漏信息，可降低至 0.1 或 0；如果 Context Window 溢出，可提高至 0.3-0.4。
2. **语言模型 (`refiner_model_path`)**: 目前默认为 `gpt2` (英文)。如果处理中文数据效果不佳，建议更换为中文 GPT2 模型（如 `uer/gpt2-chinese-cluecorpussmall`）并修改脚本中的 `lang="zh"`。
3. **Pipeline Prompt**: `SearchR1Pipeline` 使用英文 Prompt。如果 DeepSearch 数据集主要是中文，模型（Qwen2.5）通常能跨语言理解，但可能需要在 `reasoning_pipeline.py` 中或通过继承修改 Prompt 模板。

