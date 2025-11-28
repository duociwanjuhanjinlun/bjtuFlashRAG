# DeepSearch问题解决方案

## 问题1: 模型不产生任何想法和输出

### 根本原因

1. **IRCoT pipeline的stop参数过于严格**：使用了`stop=['.', '\n']`，导致生成在遇到句号或换行符时立即停止
2. **生成参数设置不当**：如果prompt本身包含这些字符，或模型第一个token就是这些字符，就会导致空输出
3. **max_tokens可能被stop参数覆盖**：即使设置了max_tokens，stop参数也会提前终止生成

### 解决方案

#### 修复1: 修改IRCoT pipeline的生成逻辑

已修改 `/root/FlashRAG/flashrag/pipeline/active_pipeline.py` 第986行：

```python
# 修改前：
new_thoughts_batch = self.generator.generate(input_prompts, stop=['.', '\n'])

# 修改后：
new_thoughts_batch = self.generator.generate(
    input_prompts, 
    max_tokens=128,  # 确保至少生成一些内容
    stop=None  # 移除stop参数，让模型自然生成
)
```

#### 修复2: 优化配置参数

创建了新的配置文件 `configs/deepsearch_ircot_fixed.yaml`：

- 增加 `retrieval_topk` 到 15，提高召回率
- 增加 `retrieval_query_max_length` 到 256
- 调整 `generation_params.max_tokens` 到 256
- 调整 `temperature` 到 0.3，增加生成多样性

### 使用方法

```bash
cd /root/deepsearch_flashrag
python scripts/run_improved_pipeline.py \
    --config configs/deepsearch_ircot_fixed.yaml \
    --pipeline ircot \
    --use-custom-prompt \
    --sample-num 25
```

---

## 问题2: 系统回答dev_0时没有提供与"Kai Tomety"相关的信息

### 问题分析

dev_0的问题是一个复杂的多跳推理问题：
- 需要找到国家队的教练
- 该教练所在国家的第一任总统曾在某公司工作
- 该公司在世界杯前一年拒绝了与食品公司的收购
- 教练在正式任命后不到5年带领国家队参加重大赛事
- 对手在第二回合退赛导致walkover

这是一个典型的**多跳推理问题**，需要：
1. 理解问题的多个约束条件
2. 逐步检索相关信息
3. 连接不同信息片段
4. 最终找到答案

### 改进建议

#### 建议1: 使用查询改写和扩展

在IRCoT pipeline中，可以改进查询生成策略：

```python
# 在生成新查询时，明确要求包含关键实体
query_prompt = f"""
Based on the question: {question}
And the current thought: {current_thought}
Generate a specific search query that includes:
1. Key entities mentioned (coach, president, company, country, tournament)
2. Time constraints (years, decades)
3. Specific events (takeover bid, world cup, walkover)
"""
```

#### 建议2: 增加检索轮数和文档数量

- 将 `retrieval_topk` 增加到 15-20
- 将 `max_iter` 增加到 5-7轮
- 使用混合检索（dense + sparse）

#### 建议3: 使用外部检索增强

对于这类复杂问题，可以考虑：

1. **Web搜索增强**：使用FlashRAG的Web Search Retriever
2. **知识图谱**：使用Trace方法构建知识图谱
3. **多源检索**：结合Wikipedia、新闻、体育数据库等

#### 建议4: 改进Prompt模板

针对复杂多跳问题，优化prompt：

```python
system_prompt = """
You are solving a complex multi-hop reasoning question. 
Follow these steps:
1. Identify all entities and constraints in the question
2. Break down the question into sub-questions
3. For each sub-question, search for relevant information
4. Connect information across different documents
5. Verify your reasoning chain
6. Provide the final answer

Remember: Complex questions often require multiple retrieval steps.
"""
```

#### 建议5: 后处理验证

添加答案验证步骤：

```python
def verify_answer(question, answer, retrieved_docs):
    """
    验证答案是否与检索到的文档一致
    """
    # 检查答案中的关键实体是否在文档中出现
    # 检查答案是否满足所有约束条件
    # 如果验证失败，触发额外检索
    pass
```

### 实施优先级

1. **立即实施**：
   - ✅ 修复IRCoT的stop参数问题（已完成）
   - ✅ 增加检索数量（已在配置中）
   - ✅ 优化生成参数（已在配置中）

2. **短期改进**：
   - 改进IRCoT的查询生成prompt
   - 增加max_iter轮数
   - 使用混合检索策略

3. **长期优化**：
   - 集成Web搜索
   - 使用知识图谱方法
   - 实现答案验证机制

### 测试建议

针对dev_0这类复杂问题，建议：

1. **单样本调试**：先用单个样本测试，观察每一步的检索和生成
2. **中间结果检查**：检查每轮迭代的检索结果和生成内容
3. **逐步优化**：根据中间结果调整参数和策略

### 预期效果

实施这些改进后，预期能够：
- ✅ 解决空输出问题（通过修复stop参数）
- ✅ 提高检索覆盖率（通过增加topk）
- ✅ 改善多跳推理能力（通过优化prompt和增加迭代）
- ⚠️ 对于极复杂的多跳问题，可能需要结合外部知识源

