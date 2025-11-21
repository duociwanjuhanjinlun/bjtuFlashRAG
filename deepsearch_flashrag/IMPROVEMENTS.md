# DeepSearch系统改进方案

## 问题分析

根据运行结果分析，当前系统存在以下主要问题：

1. **检索质量不足**：检索到的文档与问题相关性低
2. **Prompt过于简单**：默认prompt无法有效指导模型处理复杂多跳问题
3. **生成质量差**：大量空回答或重复内容
4. **缺少推理机制**：SequentialPipeline无法处理需要多步推理的复杂问题

## 改进方案

### 1. 提升检索质量

**改进点：**
- 增加 `retrieval_topk` 从 5 到 10，获取更多候选文档
- 增加 `retrieval_query_max_length` 从 96 到 128，捕获更完整的查询信息
- 使用更强的 reranker（bge-reranker-large）
- 增加 `rerank_topk` 从 5 到 8，保留更多高质量文档

**配置文件：** `configs/deepsearch_improved.yaml`

### 2. 优化Prompt模板

**改进点：**
- 设计针对复杂问题的多步骤推理prompt
- 明确指导模型分析文档、连接信息、逐步推理
- 提供更清晰的输出格式要求

**实现文件：** `prompts/deepsearch_prompt.py`

### 3. 优化生成参数

**改进点：**
- 降低 `temperature` 从 0.2 到 0.1，提高输出确定性
- 增加 `max_tokens` 从 300 到 512，允许更完整的回答
- 增加 `generator_max_input_len` 从 1024 到 2048，容纳更多上下文
- 降低 `generator_batch_size` 到 1，确保稳定性

### 4. 使用Refiner优化检索结果

**改进点：**
- 启用 `extractive` refiner，从检索文档中提取关键信息
- 减少噪声，提高输入质量

### 5. 使用多轮检索Pipeline

**推荐方案：**
- 使用 `IRCOTPipeline`（Iterative Retrieval Chain-of-Thought）
- 支持多轮检索和推理，适合复杂多跳问题
- 可以逐步细化查询，逐步获取所需信息

## 使用方法

### 方法1：使用改进的Sequential Pipeline

```bash
cd /root/deepsearch_flashrag
python scripts/run_improved_pipeline.py \
    --config configs/deepsearch_improved.yaml \
    --pipeline sequential \
    --use-custom-prompt \
    --sample-num 25
```

### 方法2：使用IRCoT多轮检索Pipeline（推荐）

```bash
python scripts/run_improved_pipeline.py \
    --config configs/deepsearch_improved.yaml \
    --pipeline ircot \
    --use-custom-prompt \
    --sample-num 25
```

### 方法3：使用Adaptive Pipeline（自动选择策略）

```bash
python scripts/run_improved_pipeline.py \
    --config configs/deepsearch_improved.yaml \
    --pipeline adaptive \
    --use-custom-prompt \
    --sample-num 25
```

## 进一步优化建议

### 1. 混合检索策略
- 结合密集检索（e5）和稀疏检索（BM25）
- 使用 `use_multi_retriever: True` 配置

### 2. 外部检索增强
- 对于实时信息，可以集成Web搜索API
- FlashRAG支持Web Search Retriever

### 3. 更大的生成模型
- 如果显存允许，使用13B或32B模型
- 或使用量化版本（4bit/8bit）

### 4. 后处理优化
- 添加答案验证和去重逻辑
- 对生成结果进行格式化和清理

### 5. 领域特定优化
- 针对特定领域（如学术、历史）优化prompt
- 使用领域特定的检索模型

## 预期效果

实施这些改进后，预期能够：
- 提高检索相关性（通过更多文档和更强reranker）
- 改善生成质量（通过优化prompt和参数）
- 处理复杂多跳问题（通过IRCoT pipeline）
- 减少空回答和重复内容（通过更好的prompt指导）

## 注意事项

1. **显存需求**：改进后的配置需要更多显存，确保GPU资源充足
2. **运行时间**：多轮检索会增加运行时间，但能显著提升质量
3. **参数调优**：根据实际效果调整 `retrieval_topk`、`rerank_topk` 等参数
4. **模型选择**：如果显存不足，可以考虑使用量化模型或更小的模型

