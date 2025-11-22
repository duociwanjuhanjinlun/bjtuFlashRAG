# DeepSearch答案精炼优化指南

## 问题分析

当前系统能够生成思考过程，但输出答案存在以下问题：

1. **输出冗长**：模型输出完整的推理过程，而不是简洁的答案
2. **格式不符**：golden_answers期望简洁答案（如"Kai Tomety"），但当前输出是推理文本
3. **缺少答案提取**：IRCoT直接拼接所有thoughts，没有提取最终答案

## 已实施的优化

### 1. 改进IRCoT Prompt模板 (`prompts/ircot_concise_prompt.py`)

- ✅ 明确要求最终答案格式："So the answer is: [answer]"
- ✅ 强调答案要简短精确，不要解释
- ✅ 提供清晰的示例说明好的和坏的输出格式

### 2. 改进答案提取逻辑 (`flashrag/pipeline/active_pipeline.py`)

- ✅ 在IRCoT pipeline的`run_batch`方法中添加答案提取
- ✅ 自动查找"So the answer is:"后的内容
- ✅ 清理和截断过长的答案
- ✅ 保存原始输出用于调试

### 3. 优化生成参数 (`configs/deepsearch_ircot_fixed.yaml`)

- ✅ 降低temperature到0.1，提高确定性
- ✅ 减少max_tokens到128，避免冗长输出

### 4. 创建改进的答案提取器 (`utils/improved_answer_extractor.py`)

提供了多种策略从文本中提取答案：
- 查找"So the answer is:"模式
- 提取实体（人名、地名等）
- 清理和截断过长文本

## 使用方法

### 运行优化后的系统

```bash
cd /root/deepsearch_flashrag
python scripts/run_improved_pipeline.py \
    --config configs/deepsearch_ircot_fixed.yaml \
    --pipeline ircot \
    --use-custom-prompt \
    --sample-num 25
```

### 使用改进的答案提取器（可选）

如果需要后处理，可以使用：

```python
from deepsearch_flashrag.utils.improved_answer_extractor import improved_ircot_pred_parse

# 在evaluate之前调用
dataset = improved_ircot_pred_parse(dataset)
```

## 进一步优化建议

### 1. 调整生成参数

如果答案仍然不够精确，可以尝试：

```yaml
generation_params:
  temperature: 0.0  # 完全确定性生成
  max_tokens: 64    # 进一步减少token数
  top_p: 0.8        # 降低top_p
```

### 2. 改进Prompt模板

可以在prompt中更明确地要求：

```
When you have the final answer, write ONLY:
"So the answer is: [answer]"

Do NOT include:
- Explanations
- Reasoning steps
- Additional context
- Multiple sentences
```

### 3. 后处理优化

可以添加后处理步骤：
- 移除常见的填充词（"the answer is", "I think", etc.）
- 提取关键实体
- 验证答案格式

### 4. 使用更大的模型

如果显存允许，可以考虑：
- 使用Qwen2.5-32B或更大的模型
- 使用专门针对问答任务微调的模型

### 5. 增加检索质量

- 提高`retrieval_topk`到15-20
- 使用混合检索（dense + sparse）
- 增加`max_iter`到5-7轮

## 预期效果

实施这些优化后，预期能够：

- ✅ 生成格式正确的答案（"So the answer is: [answer]"）
- ✅ 自动提取简洁答案
- ✅ 减少冗长输出
- ✅ 提高答案精确度

## 调试建议

如果答案仍然不理想，可以：

1. **检查中间输出**：查看`intermediate_output_iter*`中的thoughts
2. **检查原始输出**：查看`raw_pred`字段
3. **调整prompt**：根据实际输出调整prompt模板
4. **调整参数**：根据问题类型调整temperature和max_tokens

## 示例

### 优化前
```
Pred: To solve this complex question, let's break it down step-by-step: 1. We need to identify the national team coach...
```

### 优化后
```
Pred: Kai Tomety
Raw_pred: ... So the answer is: Kai Tomety
```

