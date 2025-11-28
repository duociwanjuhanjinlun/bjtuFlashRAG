# DeepSearch FlashRAG 项目说明文档

## 目录

1. [项目概述](#项目概述)
2. [数据处理](#数据处理)
3. [R1 Search Pipeline](#r1-search-pipeline)
4. [IRCoT Pipeline](#ircot-pipeline)
5. [Pipeline 对比](#pipeline-对比)
6. [配置说明](#配置说明)
7. [常见问题](#常见问题)

---

## 项目概述

DeepSearch FlashRAG 是一个基于 FlashRAG 框架的复杂问答系统，支持多跳推理和检索增强生成（RAG）。项目提供了两种主要的 Pipeline：

- **R1 Search Pipeline**：基于 DeepSeek-R1 风格的推理+搜索机制，适合需要逐步分解的复杂问题
- **IRCoT Pipeline**：迭代检索推理（Iterative Retrieval Chain-of-Thought），通过多轮迭代逐步完善答案

### 核心特性

- 🔍 **混合检索**：结合 BM25（稀疏检索）和 E5（密集检索）的优势
- 🎯 **智能重排序**：使用 Qwen3-Reranker-8B 对检索结果进行精排
- 🧠 **查询优化**：支持实体识别、查询改写和多查询策略
- 📝 **上下文压缩**：使用 Selective Context Refiner 压缩长文档
- 🔄 **多轮迭代**：支持多轮检索和推理，逐步完善答案

---

## 数据处理

### 脚本：`prepare_dataset.py`

该脚本用于将原始 JSON 格式的数据转换为 FlashRAG 所需的 JSONL 格式。

### 功能说明

- 支持有答案的数据集（训练集/验证集）和无答案的数据集（测试集）
- 自动处理 `input_field` 和 `output_field` 字段映射
- 生成符合 FlashRAG 格式的 JSONL 文件

### 使用方法

#### 处理有答案的数据集（训练集/验证集）

```bash
python deepsearch_flashrag/scripts/prepare_dataset.py \
    --source /path/to/data_dev.json \
    --target-dir /data/bjtu_deepsearch/dataset/deepsearch \
    --split dev
```

#### 处理无答案的数据集（测试集）

```bash
python deepsearch_flashrag/scripts/prepare_dataset.py \
    --source /path/to/data_a.json \
    --target-dir /data/bjtu_deepsearch/dataset/deepsearch \
    --split test \
    --no-answers
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--source` | 输入的原始 JSON 文件路径 | **必需** |
| `--target-dir` | 输出目录（JSONL 文件保存位置） | `/data/bjtu_deepsearch/dataset/deepsearch` |
| `--split` | 数据集分割名称（如 "test", "dev"） | `test` |
| `--no-answers` | 标记数据集没有正确答案（测试集） | `False` |

### 输入格式

原始 JSON 文件应包含以下字段：

```json
[
    {
        "id": "dev_1",
        "input_field": "问题内容",
        "output_field": "答案内容"  // 仅在有答案的数据集中存在
    }
]
```

### 输出格式

生成的 JSONL 文件格式：

```jsonl
{"id": "dev_1", "question": "问题内容", "golden_answers": ["答案内容"], "metadata": {}}
{"id": "dev_2", "question": "问题内容", "golden_answers": [], "metadata": {}}
```

---

## R1 Search Pipeline

### 脚本：`run_r1_search.py`

R1 Search Pipeline 实现了基于 DeepSeek-R1 风格的推理+搜索机制，通过逐步分解复杂问题并迭代检索来获得答案。

### 基本原理

#### 1. 工作流程

```
用户问题
    ↓
[第 1 轮]
生成推理 → 提取搜索查询 → 检索文档 → 重排序 → 压缩上下文
    ↓
[第 2 轮]
基于新文档继续推理 → 提取搜索查询 → 检索文档 → ...
    ↓
[第 N 轮]
生成最终答案 <answer>...</answer>
```

#### 2. 核心机制

**推理分解（Reasoning Decomposition）**
- 模型在 `<think>` 标签内进行思维链推理
- 将复杂问题分解为多个子问题
- 识别每一步需要检索的关键信息

**逐步搜索（Step-by-Step Search）**
- 每次只搜索一个具体的子问题
- 使用 `<search>查询关键词</search>` 标签触发检索
- 查询关键词应简洁、聚焦实体，避免冗长描述

**迭代完善（Iterative Refinement）**
- 每轮检索后，模型基于新文档继续推理
- 如果信息不足，继续生成新的搜索查询
- 直到获得足够信息，生成最终答案

#### 3. 关键特性

**查询优化（Query Improvement）**
- **实体识别（NER）**：使用 spaCy 提取关键实体
- **查询改写**：基于问题和当前推理改进查询
- **多查询策略**：为每个问题生成多个查询变体，提高召回率

**混合检索（Hybrid Retrieval）**
- **BM25**：擅长精确匹配专有名词
- **E5**：擅长语义匹配和理解
- **RRF 融合**：使用 Reciprocal Rank Fusion 合并两种检索结果

**上下文压缩（Context Refinement）**
- 使用 Selective Context Refiner 压缩检索到的文档
- 保留关键信息，减少输入长度
- 可配置压缩率（`reduce_ratio`）

### 使用方法

#### 基本运行

```bash
python deepsearch_flashrag/scripts/run_r1_search.py \
    --config deepsearch_flashrag/configs/r1_search_v1.yaml \
    --split test \
    --sample-num 10
```

#### 自定义数据路径

```bash
python deepsearch_flashrag/scripts/run_r1_search.py \
    --config deepsearch_flashrag/configs/r1_search_v1.yaml \
    --split test \
    --data-dir /custom/data/path \
    --output-dir /custom/output/path \
    --sample-num 20
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config` | 配置文件路径 | `configs/r1_search_v1.yaml` |
| `--split` | 数据集分割名称 | `test` |
| `--data-dir` | 数据目录（覆盖配置文件） | `None` |
| `--output-dir` | 输出目录（覆盖配置文件） | `None` |
| `--sample-num` | 测试样本数量（覆盖配置文件） | `None` |

### 输出结果

Pipeline 会生成以下文件：

1. **中间结果** (`intermediate_data.json`)：包含每步的详细输出
   - `prompt`：完整的 prompt（包含所有检索文档）
   - `raw_pred`：模型原始输出（累积所有步骤）
   - `retrieval_results`：每轮的检索结果
   - `retrieved_times`：检索轮数

2. **最终结果** (`output.jsonl`)：包含预测答案和评估指标
   - `id`：样本 ID
   - `pred`：预测答案
   - `golden_answers`：正确答案（如果有）
   - `em`、`f1`：评估指标

### 配置要点

#### 生成器配置

```yaml
generator_model: "Qwen/Qwen2.5-32B-Instruct"
generator_batch_size: 1  # 受显存限制，通常只能设为 1
generation_params:
  max_tokens: 4096  # 每步生成的最大 token 数
  temperature: 0.5  # 推理任务建议 0.3-0.6
```

#### 检索配置

```yaml
multi_retriever_setting:
  merge_method: "rrf"  # 使用 RRF 融合
  rrf_k: 20  # RRF 超参数，值越小 BM25 权重越高
  retriever_list:
    - retrieval_method: "bm25"
      retrieval_topk: 20
    - retrieval_method: "e5"
      retrieval_topk: 20
      instruction: "query: "  # E5 模型必需的前缀
```

#### Pipeline 配置

```yaml
max_iter: 4  # 最大检索轮数
active_retrieval_k: 3  # 激活检索的最小查询数
```

#### 查询优化配置

```yaml
query_improver_config:
  enabled: True  # 启用查询优化
  use_ner: True  # 使用 NER 提取实体
  multi_query: True  # 使用多查询策略
  multi_query_num: 2  # 每个问题生成 2 个查询变体
```

---

## IRCoT Pipeline

### 脚本：`run_improved_pipeline.py`

IRCoT（Iterative Retrieval Chain-of-Thought）Pipeline 通过多轮迭代检索和推理，逐步完善答案。

### 基本原理

#### 1. 工作流程

```
用户问题 + 初始文档
    ↓
[第 1 轮]
生成思考（Thought） → 判断是否需要更多信息
    ↓ [需要]
检索新文档 → 合并上下文
    ↓
[第 2 轮]
基于新文档继续思考 → 判断是否需要更多信息
    ↓
[第 N 轮]
生成最终答案 "So the answer is: ..."
```

#### 2. 核心机制

**迭代推理（Iterative Reasoning）**
- 每轮生成一个思考步骤（Thought）
- 思考步骤应简洁、聚焦，避免冗长解释
- 基于当前文档和问题，判断是否需要检索更多信息

**自动检索触发**
- 模型在思考过程中识别信息缺口
- 自动生成搜索查询并触发检索
- 检索结果自动添加到上下文

**答案格式规范**
- 英文问题：`So the answer is: [答案]`
- 中文问题：`答案是：[答案]`
- 答案应简短精确，不包含额外解释

#### 3. 关键特性

**简洁思考生成**
- 强调一次只生成一个思考步骤
- 避免一次性生成所有推理步骤
- 每个思考应明确、具体

**上下文管理**
- 自动管理多轮检索的文档
- 支持长上下文（最大 5120 tokens）
- 使用 reranker 筛选最相关文档

### 使用方法

#### 基本运行（使用 IRCoT Pipeline）

```bash
python deepsearch_flashrag/scripts/run_improved_pipeline.py \
    --config deepsearch_flashrag/configs/deepsearch_ircot_fixed.yaml \
    --pipeline ircot \
    --split test \
    --sample-num 10
```

#### 使用自定义 Prompt

```bash
python deepsearch_flashrag/scripts/run_improved_pipeline.py \
    --config deepsearch_flashrag/configs/deepsearch_ircot_fixed.yaml \
    --pipeline ircot \
    --split test \
    --use-custom-prompt \
    --sample-num 10
```

#### 使用其他 Pipeline 类型

```bash
# Sequential Pipeline
python deepsearch_flashrag/scripts/run_improved_pipeline.py \
    --pipeline sequential \
    --config deepsearch_flashrag/configs/deepsearch_ircot_fixed.yaml

# Conditional Pipeline
python deepsearch_flashrag/scripts/run_improved_pipeline.py \
    --pipeline conditional \
    --config deepsearch_flashrag/configs/deepsearch_ircot_fixed.yaml

# Adaptive Pipeline
python deepsearch_flashrag/scripts/run_improved_pipeline.py \
    --pipeline adaptive \
    --config deepsearch_flashrag/configs/deepsearch_ircot_fixed.yaml
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--config` | 配置文件路径 | `configs/deepsearch_improved.yaml` |
| `--pipeline` | Pipeline 类型（sequential/conditional/adaptive/ircot） | `ircot` |
| `--split` | 数据集分割名称 | `None`（使用配置文件） |
| `--data-dir` | 数据目录（覆盖配置文件） | `None` |
| `--output-dir` | 输出目录（覆盖配置文件） | `None` |
| `--sample-num` | 测试样本数量（覆盖配置文件） | `None` |
| `--use-custom-prompt` | 使用优化的 Prompt 模板 | `False` |
| `--skip-eval` | 跳过评估指标计算 | `False` |

### 配置要点

#### 生成器配置

```yaml
generator_model: "Qwen/Qwen2.5-14B-Instruct-1M"
generator_batch_size: 1
generation_params:
  temperature: 0.1  # 较低温度，提高确定性
  max_tokens: 1024  # 每次迭代的 token 数
```

#### 检索配置

```yaml
retrieval_method: "e5"
retrieval_topk: 20  # 检索文档数量
retrieval_query_max_length: 512
```

#### Reranker 配置

```yaml
use_reranker: True
rerank_model_name: "Qwen3-Reranker-8B"
rerank_topk: 8  # 重排序后保留的文档数
```

---

## Pipeline 对比

### R1 Search vs IRCoT

| 特性 | R1 Search Pipeline | IRCoT Pipeline |
|------|-------------------|----------------|
| **推理方式** | 显式分解问题，逐步搜索 | 迭代思考，自动触发检索 |
| **查询生成** | 使用 `<search>` 标签显式生成 | 在思考中隐式生成 |
| **答案格式** | `<answer>答案</answer>` | `So the answer is: 答案` |
| **适用场景** | 需要明确分解的多跳问题 | 需要逐步推理的复杂问题 |
| **检索控制** | 完全由模型控制 | 由 Pipeline 自动管理 |
| **查询优化** | 支持 NER、多查询策略 | 依赖模型自身能力 |
| **上下文压缩** | 支持 Selective Context | 不支持 |
| **混合检索** | 支持 BM25 + E5 | 仅支持单一检索器 |

### 选择建议

**使用 R1 Search Pipeline 当：**
- 问题需要明确的步骤分解
- 需要精确控制检索查询
- 需要利用查询优化功能
- 需要混合检索的优势

**使用 IRCoT Pipeline 当：**
- 问题需要逐步推理
- 希望模型自动判断检索时机
- 需要更自然的推理过程
- 资源有限（IRCoT 通常使用更小的模型）

---

## 配置说明

### 关键配置项

#### 1. 生成器配置

```yaml
generator_model: "Qwen/Qwen2.5-32B-Instruct"  # 模型名称
generator_batch_size: 1  # 批次大小（受显存限制）
generator_max_input_len: 16384  # 最大输入长度
generation_params:
  temperature: 0.5  # 温度参数（0.3-0.6 适合推理）
  max_tokens: 4096  # 每步最大生成 token 数
  top_p: 0.95  # 核采样参数
gpu_memory_utilization: 0.98  # GPU 显存利用率
```

#### 2. 检索配置

**混合检索（R1 Search）**
```yaml
multi_retriever_setting:
  merge_method: "rrf"  # 融合方法：rrf 或 weighted
  topk: 30  # 融合后的 topk
  rrf_k: 20  # RRF 超参数（20-60，越小 BM25 权重越高）
  retriever_list:
    - retrieval_method: "bm25"
      retrieval_topk: 20
    - retrieval_method: "e5"
      retrieval_topk: 20
      instruction: "query: "  # E5 必需的前缀
```

**单一检索（IRCoT）**
```yaml
retrieval_method: "e5"
retrieval_topk: 20
retrieval_query_max_length: 512
```

#### 3. Reranker 配置

```yaml
use_reranker: True
rerank_model_name: "Qwen3-Reranker-8B"
rerank_topk: 10  # 重排序后保留的文档数
rerank_batch_size: 4
rerank_max_length: 8192
```

#### 4. Refiner 配置（仅 R1 Search）

```yaml
use_refiner: True
refiner_name: "selective-context"
refiner_config:
  reduce_ratio: 0.35  # 压缩率（0.2-0.5，越小保留越多信息）
  reduce_level: "phrase"  # 压缩级别：phrase 或 sentence
```

#### 5. 查询优化配置（仅 R1 Search）

```yaml
query_improver_config:
  enabled: True  # 启用查询优化
  use_ner: True  # 使用 NER（需要安装 spaCy）
  multi_query: True  # 多查询策略
  multi_query_num: 2  # 每个问题生成的查询变体数
```

#### 6. Pipeline 配置

```yaml
max_iter: 4  # 最大迭代轮数
active_retrieval_k: 3  # 激活检索的最小查询数（R1 Search）
```

### 性能优化建议

1. **减少生成 Token 数**：将 `max_tokens` 从 4096 降至 1024-1536，可提升 2-3 倍速度
2. **降低 Temperature**：从 0.5 降至 0.3-0.4，可提升 10-20% 速度
3. **减少检索轮数**：将 `max_iter` 从 4 降至 3，可节省 20-30% 时间
4. **减少 TopK**：降低 `retrieval_topk` 和 `rerank_topk`，可减少上下文长度
5. **提前终止**：检测到答案后立即停止，可节省 25-50% 时间

---

## 常见问题

### 1. 显存不足（OOM）

**问题**：运行时报错 `CUDA out of memory`

**解决方案**：
- 降低 `generator_batch_size` 至 1
- 降低 `gpu_memory_utilization` 至 0.85-0.90
- 减少 `generator_max_input_len` 至 8192 或更小
- 减少 `max_tokens` 和 `max_new_tokens`
- 减少检索 TopK 值

### 2. 维度不匹配错误

**问题**：`The size of tensor a (1024) must match the size of tensor b (512)`

**原因**：E5 编码器的输出维度与 FAISS 索引的维度不匹配

**解决方案**：
- 检查 E5 模型版本是否与索引构建时使用的模型一致
- 确认 `retrieval_query_max_length` 设置正确（通常为 512 或 1024）
- 检查索引文件是否正确

### 3. 答案提取失败

**问题**：`finish_reason: "Normal finish without answer pattern"`

**原因**：
- 模型输出未包含 `<answer>` 标签（R1 Search）
- 模型输出未包含 `So the answer is:` 格式（IRCoT）
- `raw_pred` 被截断，导致标签不完整

**解决方案**：
- 增加 `max_tokens` 确保完整输出
- 检查 `raw_pred` 是否包含完整标签
- 调整 prompt 强调答案格式要求

### 4. 检索结果为空

**问题**：检索返回空结果

**原因**：
- 查询格式不正确（E5 缺少 `query: ` 前缀）
- 索引路径错误
- 维度不匹配导致检索失败

**解决方案**：
- 确认 E5 配置中包含 `instruction: "query: "`
- 检查索引文件路径是否正确
- 查看日志中的维度错误信息

### 5. 查询优化失败

**问题**：`WARNING: Query improvement failed`

**原因**：
- spaCy 模型未安装（如果启用 NER）
- 查询为空或格式错误

**解决方案**：
- 安装 spaCy：`pip install spacy && python -m spacy download en_core_web_sm`
- 检查查询是否为空
- 如果不需要 NER，设置 `use_ner: False`

### 6. 生成速度慢

**问题**：Pipeline 运行速度很慢

**解决方案**：
- 参考 [性能优化建议](#性能优化建议)
- 减少 `max_tokens` 至 1024-1536
- 降低 `temperature` 至 0.3-0.4
- 减少 `max_iter` 至 3
- 考虑使用更小的模型（如 14B 而非 32B）

### 7. 答案质量下降

**问题**：优化后答案准确率下降

**解决方案**：
- 逐步优化，每次只调整一个参数
- 在小样本上测试每个优化方案
- 监控 `intermediate_data.json` 中的 `raw_pred` 和 `retrieval_results`
- 必要时回退优化方案

---

## 文件结构

```
deepsearch_flashrag/
├── configs/              # 配置文件
│   ├── r1_search_v1.yaml          # R1 Search Pipeline 配置
│   └── deepsearch_ircot_fixed.yaml # IRCoT Pipeline 配置
├── scripts/              # 运行脚本
│   ├── prepare_dataset.py          # 数据预处理脚本
│   ├── run_r1_search.py           # R1 Search Pipeline 运行脚本
│   └── run_improved_pipeline.py   # IRCoT Pipeline 运行脚本
├── prompts/              # Prompt 模板
│   ├── r1_concise_prompt.py       # R1 Search Prompt
│   └── ircot_concise_prompt.py    # IRCoT Prompt
├── utils/                # 工具函数
│   ├── r1_answer_extractor.py     # 答案提取器
│   └── query_improver.py           # 查询优化器
└── README.md             # 本文档
```

---

## 更新日志

- **2024-XX-XX**：初始版本，包含 R1 Search 和 IRCoT 两个 Pipeline
- **2024-XX-XX**：添加查询优化功能（NER、多查询策略）
- **2024-XX-XX**：添加 Selective Context Refiner 支持
- **2024-XX-XX**：优化答案提取逻辑，修复 "and" 提取问题
- **2024-XX-XX**：添加混合检索（BM25 + E5）和 RRF 融合

---

## 联系方式

如有问题或建议，请提交 Issue 或联系项目维护者。

