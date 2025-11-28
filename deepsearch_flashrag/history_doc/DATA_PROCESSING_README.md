# 数据处理脚本使用说明

## 1. 将中间结果转换为提交格式

### 脚本：`convert_to_submission.py`

将 `intermediate_data.json` 转换为与 `提交示例.jsonl` 一致的格式。

**使用方法：**

```bash
# 使用默认路径（输入: /root/intermediate_data.json，输出: /root/submission.jsonl）
python deepsearch_flashrag/scripts/convert_to_submission.py

# 指定输入和输出路径
python deepsearch_flashrag/scripts/convert_to_submission.py \
    --input /root/intermediate_data.json \
    --output /root/submission.jsonl
```

**功能说明：**
- 从 `intermediate_data.json` 中提取每个样本的 `output.pred` 字段作为答案
- 转换为格式：`{"id": "xxx", "output_field": "答案"}`
- 如果 `pred` 为空，会使用 "No valid answer found" 作为默认值

**输出格式示例：**
```jsonl
{"id": "dev_0", "output_field": "Kai Tomety"}
{"id": "dev_1", "output_field": "Cinematography, 2012"}
```

---

## 2. 处理数据集（有正确答案）

### 脚本：`prepare_dataset.py`

将原始 JSON 数据集转换为 FlashRAG 格式的 jsonl。

**处理有正确答案的数据集（如 `data_dev.json`）：**

```bash
python deepsearch_flashrag/scripts/prepare_dataset.py \
    --source /root/data_dev.json \
    --target-dir /data/bjtu_deepsearch/dataset/deepsearch \
    --split dev
```

**说明：**
- `--source`: 输入的 JSON 文件路径（包含 `input_field` 和 `output_field`）
- `--target-dir`: 输出目录（默认: `/data/bjtu_deepsearch/dataset/deepsearch`）
- `--split`: 数据集分割名称（如 `dev`, `test`，默认: `test`）

**输出格式：**
```jsonl
{"id": "dev_0", "question": "...", "golden_answers": ["Kai Tomety"], "metadata": {}}
```

---

## 3. 处理测试集（无正确答案）

### 处理没有正确答案的测试集（如 `data_a.json`）：

```bash
python deepsearch_flashrag/scripts/prepare_dataset.py \
    --source /root/data_a.json \
    --target-dir /data/bjtu_deepsearch/dataset/deepsearch \
    --split test \
    --no-answers
```

**关键参数：**
- `--no-answers`: 指定数据集没有正确答案，`golden_answers` 将设置为空列表 `[]`

**输出格式：**
```jsonl
{"id": "a_0", "question": "...", "golden_answers": [], "metadata": {}}
```

---

## 完整工作流程示例

### 场景 1：处理开发集（有正确答案）

```bash
# 1. 转换数据集格式
python deepsearch_flashrag/scripts/prepare_dataset.py \
    --source /root/data_dev.json \
    --target-dir /data/bjtu_deepsearch/dataset/deepsearch \
    --split dev

# 2. 运行 R1 Search Pipeline
python deepsearch_flashrag/scripts/run_r1_search.py \
    --config deepsearch_flashrag/configs/r1_search_v1.yaml \
    --split dev

# 3. 将中间结果转换为提交格式
python deepsearch_flashrag/scripts/convert_to_submission.py \
    --input /root/intermediate_data.json \
    --output /root/dev_submission.jsonl
```

### 场景 2：处理测试集（无正确答案）

```bash
# 1. 转换测试集格式（注意使用 --no-answers）
python deepsearch_flashrag/scripts/prepare_dataset.py \
    --source /root/data_a.json \
    --target-dir /data/bjtu_deepsearch/dataset/deepsearch \
    --split test \
    --no-answers

# 2. 运行 R1 Search Pipeline
python deepsearch_flashrag/scripts/run_r1_search.py \
    --config deepsearch_flashrag/configs/r1_search_v1.yaml \
    --split test

# 3. 将中间结果转换为提交格式
python deepsearch_flashrag/scripts/convert_to_submission.py \
    --input /root/intermediate_data.json \
    --output /root/test_submission.jsonl
```

---

## 参数说明

### `convert_to_submission.py` 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input` | 输入的 `intermediate_data.json` 文件路径 | `/root/intermediate_data.json` |
| `--output` | 输出的 jsonl 文件路径 | `/root/submission.jsonl` |

### `prepare_dataset.py` 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--source` | 输入的 JSON 文件路径（必需） | - |
| `--target-dir` | 输出目录 | `/data/bjtu_deepsearch/dataset/deepsearch` |
| `--split` | 数据集分割名称 | `test` |
| `--no-answers` | 数据集没有正确答案（测试集） | `False` |

---

## 注意事项

1. **测试集处理**：处理 `data_a.json` 时必须使用 `--no-answers` 参数，因为该文件没有 `output_field` 字段。

2. **路径设置**：确保 `--target-dir` 目录存在或脚本有权限创建。

3. **编码问题**：所有脚本使用 UTF-8 编码，支持中文字符。

4. **空答案处理**：如果 `intermediate_data.json` 中某个样本的 `pred` 为空，`convert_to_submission.py` 会使用 "No valid answer found" 作为默认值。

