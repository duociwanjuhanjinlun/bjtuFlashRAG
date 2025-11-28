# 空查询错误修复说明

## 问题描述

在使用 IRCoT pipeline 和 Qwen3-Reranker-8B 时，遇到以下错误：

```
RuntimeError: cannot reshape tensor of 0 elements into shape [4, 0, -1, 128] because the unspecified dimension size -1 can be any value and is ambiguous
```

**根本原因：** IRCoT pipeline 在生成推理步骤时，有时会产生空字符串作为查询，而 Qwen3-Reranker-8B 模型无法处理空输入。

## 修复方案

### 1. 在 Encoder 层面修复 (`flashrag/retriever/encoder.py`)

在 `single_batch_encode` 方法中，过滤空查询并用占位符替换：

```python
# 过滤空查询，用占位符替换以避免模型错误
processed_query_list = []
for q in query_list:
    if q and q.strip():
        processed_query_list.append(q)
    else:
        processed_query_list.append(" ")  # 使用单个空格作为占位符
```

### 2. 在 Reranker 层面修复 (`flashrag/retriever/reranker.py`)

在 `BiReranker.get_rerank_scores` 方法中，在调用 encoder 之前过滤空查询：

```python
# 过滤空查询，用占位符替换
processed_query_list = []
for query in query_list:
    if query and query.strip():
        processed_query_list.append(query)
    else:
        processed_query_list.append(" ")  # 使用单个空格作为占位符
```

### 3. 在 Pipeline 层面修复 (`flashrag/pipeline/active_pipeline.py`)

在 IRCoT pipeline 的 `run_batch` 方法中，在传递给 retriever 之前过滤空查询：

```python
# 过滤空查询，用占位符替换
processed_thoughts = []
for thought in new_thoughts_for_retrieval:
    if thought and thought.strip():
        processed_thoughts.append(thought)
    else:
        processed_thoughts.append(" ")  # 使用单个空格作为占位符
```

## 修复效果

- ✅ 防止空查询导致模型错误
- ✅ 使用占位符（单个空格）确保模型能正常处理
- ✅ 在多个层面进行防护，提高系统鲁棒性

## 测试建议

修复后，可以重新运行 IRCoT pipeline：

```bash
cd /root/deepsearch_flashrag
python scripts/run_improved_pipeline.py \
    --config configs/deepsearch_improved.yaml \
    --pipeline ircot \
    --use-custom-prompt \
    --sample-num 25
```

## 注意事项

1. 使用单个空格 `" "` 作为占位符，而不是完全空字符串
2. 这确保了 tokenizer 能够正确处理输入
3. 虽然占位符查询的检索结果可能不太相关，但不会导致系统崩溃
4. 如果 IRCoT 频繁生成空查询，可能需要优化 prompt 或生成参数

