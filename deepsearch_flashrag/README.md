# DeepSearch FlashRAG 系统

本项目在 `FlashRAG` 工具箱基础上，针对 bjtuDeepSearch 赛题构建一个可扩展的多阶段 RAG 系统。系统使用 `/public/modelscope-datasets/hhjinjiajie/FlashRAG_Dataset` 提供的检索语料与索引，数据与产出统一落盘到 `/data`，实现从数据整理、配置管理到推理评测的完整链路。

## 系统架构

- **数据层**：`/data/bjtu_deepsearch/dataset/deepsearch/test.jsonl` 存放经过 `scripts/prepare_dataset.py` 转换后的赛题输入；外部知识使用 `wiki18_100w` 语料及其 `e5` 索引。
- **判别层**：`Adaptive Judger` (`illuminoplanet/adaptive-rag-classifier`) 根据问题难度将输入划分为「无需检索 / 单跳检索 / 多跳检索」，对应 `AdaptivePipeline` 中的三条子路径（零样本、标准 Sequential、IRCOT reasoning）。
- **检索层**：默认 `intfloat/e5-base-v2` + wiki18_100w 索引检索 `topk=8`，可选启用缓存；可在配置里切换 `bm25` 或多检索器。
- **排序/压缩层**：`BAAI/bge-reranker-large` 对检索结果二次排序；预留 `llmlingua`、`Selective-Context` 等精炼器配置位以压缩上下文。
- **生成层**：默认使用 `OpenAI` 框架（如 `gpt-4o-mini`），也可以在配置里切换为本地 `fschat`/`vllm`。Prompt 通过 `PromptTemplate` 将压缩后的参考文档注入，必要时可启用 `FiD`。
- **评测层**：借助 FlashRAG `Evaluator` 计算 `EM/F1` 等指标，并将中间结果与指标写入 `/data/bjtu_deepsearch/output/`。

整体流程：  
`Raw JSON → prepare_dataset → Adaptive Judger → (Sequential / IRCOT) → Retriever + Reranker + (Refiner) → PromptTemplate → Generator → Evaluator/Artifacts`

## 快速开始

1. **安装依赖**
   ```bash
   cd /root/FlashRAG
   pip install -e .[full]  # 需 Python 3.10+
   ```
   如需 OpenAI / 自建大模型，请事先配置好对应运行环境。

2. **准备数据**
   ```bash
   cd /root
   python deepsearch_flashrag/scripts/prepare_dataset.py \
     --source /root/data_dev.json \
     --target-dir /data/bjtu_deepsearch/dataset/deepsearch \
     --split test
   ```
   输出 `test.jsonl` 即可供 FlashRAG 读取。若有更多拆分，可重复执行脚本。

3. **运行管线**
   ```bash
   cd /root/deepsearch_flashrag
   # 需要先设置 OPENAI_API_KEY / OPENAI_BASE_URL（如使用 OpenAI 框架）
   python scripts/run_pipeline.py \
     --config configs/deepsearch_adaptive.yaml \
     --pipeline adaptive \
     --split test
   ```
   - `--pipeline sequential/conditional/adaptive` 可切换不同推理流程。
   - `--data-dir /path/to/data` 或 `--output-dir /path/to/output` 可在命令行覆盖配置路径。
   - `--skip-eval` 用于仅生成答案不计算指标。

4. **查看结果**
   - 预测数据、检索结果、Prompt、副产物默认写入 `/data/bjtu_deepsearch/output/<timestamp>/`
   - 评测指标记录于同目录的 `metric_score.txt`

## 目录结构

```
deepsearch_flashrag/
├── configs/
│   └── deepsearch_adaptive.yaml   # 主配置
├── prompts/                       # 可扩展自定义 prompt
├── pipelines/                     # 自定义管线放置位置（预留）
├── scripts/
│   ├── prepare_dataset.py         # JSON → JSONL
│   └── run_pipeline.py            # 统一入口
└── README.md
```

## 配置要点

- **检索资源**：`configs/deepsearch_adaptive.yaml` 默认引用 `/public/modelscope-datasets/hhjinjiajie/FlashRAG_Dataset/retrieval_corpus/wiki18_100w_e5.index` 与对应语料，无需重复下载。
- **数据落盘**：`data_dir`/`save_dir` 都指向 `/data/bjtu_deepsearch/…`，如需迁移只需覆盖脚本或命令参数。
- **判别器**：可在 `judger_config` 中替换为自训练模型；若无需判别，改用 `SequentialPipeline` 即可。
- **生成模型**：将 `framework` 改为 `vllm`/`fschat`/`hf` 并配置 `generator_model_path` 即可使用本地权重。

## 下一步建议

- 构建专用文档库（企业文档、外部 API 结果）并通过 FlashRAG 的 `index_builder` 生成自定义索引。
- 在 `pipelines/` 中实现面向赛题的多策略深度检索（例如结合同义改写或 Tree-of-Thought 推理）。
- 扩充 `prompts/`，针对不同任务类型（事实问答 / 逻辑推理）动态切换提示模版。

## debug和修复
### 收集程序日志：
```
  cd /root/deepsearch_flashrag
  PYTHONUNBUFFERED=1 \
  python scripts/run_pipeline.py --config configs/deepsearch_adaptive.yaml \
    --pipeline sequential --split test \
    2>&1 | tee /tmp/run_pipeline_$(date +%H%M).log
```
如果ssh突然断开，看/tmp/run_pipeline_*.log的最后几行锁定崩溃原因

### 监控
使用htop命令可以监控内存资源，或watch命令：
  watch -n1 "nvidia-smi; echo; free -h"
若看到 GPU/内存突然暴增直至 100%，说明还是资源问题；若资源平稳却会话断开，更可能是网络/空闲超时。

