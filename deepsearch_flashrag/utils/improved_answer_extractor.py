"""
改进的答案提取器，用于从IRCoT输出中提取精炼答案
支持中英文答案提取
"""
import re


def extract_final_answer(text: str) -> str:
    """
    从IRCoT生成的文本中提取最终答案（支持中英文）
    
    策略：
    1. 查找"So the answer is:"或"答案是："后的内容
    2. 查找最后一个句号或换行前的关键信息
    3. 提取人名、地名、数字等实体（中英文）
    4. 如果找不到，返回第一个合理的短语
    """
    if not text or not text.strip():
        return ""
    
    text = text.strip()
    
    # 策略1: 查找答案标记后的内容（支持中英文）
    patterns = [
        # 英文格式
        r"So the answer is:\s*(.+?)(?:\.|$|\n)",
        r"So the answer is:\s*(.+)",
        r"answer is:\s*(.+?)(?:\.|$|\n)",
        r"final answer is:\s*(.+?)(?:\.|$|\n)",
        r"the answer:\s*(.+?)(?:\.|$|\n)",
        # 中文格式
        r"答案是[：:]\s*(.+?)(?:[。\.]|$|\n)",
        r"答案是[：:]\s*(.+)",
        r"答案[：:]\s*(.+?)(?:[。\.]|$|\n)",
        r"最终答案是[：:]\s*(.+?)(?:[。\.]|$|\n)",
        r"所以答案是[：:]\s*(.+?)(?:[。\.]|$|\n)",
        # 混合格式
        r"answer[：:]\s*(.+?)(?:[。\.]|$|\n)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            answer = match.group(1).strip()
            # 清理答案：移除多余的标点和空格
            answer = re.sub(r'^[：:\-\s]+', '', answer)
            answer = re.sub(r'[：:\-\s]+$', '', answer)
            # 如果答案太长，只取第一句或前100个字符
            if len(answer) > 100:
                # 尝试找到第一个句号（中英文）
                first_period = min(
                    answer.find('.'), 
                    answer.find('。'),
                    answer.find('\n')
                )
                if first_period > 0:
                    answer = answer[:first_period].strip()
                else:
                    answer = answer[:100].strip()
            if answer:
                return answer
    
    # 策略2: 如果包含明确的实体（人名、地名等），尝试提取（支持中英文）
    # 查找英文人名（大写字母开头）
    english_name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
    english_names = re.findall(english_name_pattern, text)
    
    # 查找中文人名/地名（2-4个中文字符，可能包含数字和标点）
    chinese_pattern = r'([\u4e00-\u9fff]{2,10}(?:[，,、][\u4e00-\u9fff]{2,10})*)'
    chinese_entities = re.findall(chinese_pattern, text)
    
    # 优先返回中文实体（通常在答案位置）
    if chinese_entities:
        # 返回最后一个找到的中文实体（通常是最终答案）
        return chinese_entities[-1]
    
    if english_names:
        # 返回最后一个找到的英文名字（通常是最终答案）
        return english_names[-1]
    
    # 策略3: 提取最后一个合理的短语（支持中英文）
    # 移除常见的推理前缀（中英文）
    cleaned = re.sub(
        r'^(To solve|Let me|I need|We need|Based on|According to|要解决|让我|我需要|我们需要|基于|根据).*?[：:\s]*', 
        '', 
        text, 
        flags=re.IGNORECASE | re.DOTALL
    )
    cleaned = cleaned.strip()
    
    # 如果清理后的文本仍然很长，只取第一句
    if len(cleaned) > 150:
        # 尝试找到第一个句号（中英文）
        first_period = min(
            cleaned.find('.') if cleaned.find('.') > 0 else len(cleaned),
            cleaned.find('。') if cleaned.find('。') > 0 else len(cleaned),
            cleaned.find('\n') if cleaned.find('\n') > 0 else len(cleaned)
        )
        if first_period < len(cleaned) and first_period > 0:
            cleaned = cleaned[:first_period].strip()
        else:
            # 如果没有句号，取前100个字符（支持中文）
            cleaned = cleaned[:100].strip()
    
    return cleaned if cleaned else text[:100].strip()


def improved_ircot_pred_parse(dataset):
    """
    改进的IRCoT答案提取函数
    """
    for item in dataset:
        pred = item.pred if hasattr(item, 'pred') else item.get('output', {}).get('pred', '')
        if not pred:
            pred = ""
        
        # 提取精炼答案
        extracted_answer = extract_final_answer(pred)
        
        # 保存原始预测和提取的答案
        if hasattr(item, 'update_output'):
            item.update_output('raw_pred', pred)
            item.update_output('pred', extracted_answer)
        else:
            # 如果是字典格式
            if 'output' not in item:
                item['output'] = {}
            item['output']['raw_pred'] = pred
            item['output']['pred'] = extracted_answer
    
    return dataset

