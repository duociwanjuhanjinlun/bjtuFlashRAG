"""
R1 Pipeline 专用的答案提取器
专门处理 <answer> 标签（即使没有闭合标签）
"""
import re
from typing import Optional

# 无意义的单词列表，如果提取的答案只是这些单词，应该拒绝
MEANINGLESS_WORDS = {
    'and', 'or', 'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'to', 'of', 'in', 'on', 'at', 'for',
    'with', 'by', 'from', 'as', 'it', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'we', 'they',
    '和', '或', '的', '是', '在', '有', '了', '着', '就', '都', '也', '还', '又', '而', '但', '如果', '因为'
}


def extract_r1_answer(text: str, begin_token: str = "<answer>", end_token: str = "</answer>") -> Optional[str]:
    """
    从 R1 Pipeline 生成的文本中提取答案
    
    策略：
    1. 优先查找完整的 <answer>...</answer> 标签
    2. 如果没有闭合标签，查找 <answer> 后的内容直到文本末尾或下一个标签
    3. 清理答案，移除多余的空格和标点
    4. 验证答案不是无意义的单词
    5. 严格避免从 prompt 指令中提取（如 "inside <answer> and </answer>"）
    """
    if not text or not text.strip():
        return None
    
    text = text.strip()
    
    # 严格避免从 prompt 指令中提取
    # 如果文本包含 "inside <answer> and </answer>" 或类似的说明文本，跳过这些匹配
    # 使用负向前瞻和后顾来排除这些情况
    instruction_patterns = [
        r'(?:inside|output|provide|put|place).*?<answer>.*?and.*?</answer>',
        r'<answer>.*?and.*?</answer>.*?(?:tag|format|example)',
    ]
    
    # 策略1: 查找完整的 <answer>...</answer> 标签
    # 但排除在指令中的匹配
    full_pattern = rf"{re.escape(begin_token)}(.+?){re.escape(end_token)}"
    matches = list(re.finditer(full_pattern, text, re.DOTALL | re.IGNORECASE))
    
    for match in matches:
        # 检查这个匹配是否在指令文本中
        match_start = match.start()
        match_end = match.end()
        context_before = text[max(0, match_start - 100):match_start]
        context_after = text[match_end:min(len(text), match_end + 100)]
        
        # 如果前后文包含指令关键词，跳过这个匹配
        is_instruction = False
        for pattern in instruction_patterns:
            if re.search(pattern, context_before + match.group() + context_after, re.IGNORECASE):
                is_instruction = True
                break
        
        if not is_instruction:
            answer = match.group(1).strip()
            if answer:
                cleaned = _clean_answer(answer)
                # CRITICAL: 最终验证，拒绝无意义单词
                if cleaned.lower().strip() in ['and', 'or', 'the', 'a', 'an']:
                    return None
                if is_valid_answer(cleaned):
                    return cleaned
    
    # 策略2: 查找 <answer> 标签但没有闭合标签的情况
    # 从最后一个 <answer> 开始提取到文本末尾或下一个标签
    # 但必须排除指令中的 <answer>
    begin_pos = text.rfind(begin_token)
    if begin_pos != -1:
        # 检查这个 <answer> 是否在指令中
        context_before = text[max(0, begin_pos - 100):begin_pos]
        is_instruction = any(
            re.search(pattern, context_before, re.IGNORECASE) 
            for pattern in instruction_patterns
        )
        
        if not is_instruction:
            # 找到 <answer> 后的内容
            start_pos = begin_pos + len(begin_token)
            remaining_text = text[start_pos:].strip()
            
            # 如果找到 </answer>，提取到那里
            end_pos = remaining_text.find(end_token)
            if end_pos != -1:
                answer = remaining_text[:end_pos].strip()
            else:
                # 没有闭合标签，提取到下一个标签或文本末尾
                # 查找下一个可能的标签（<search>, <information>, <think> 等）
                next_tag_pattern = r'<(?:search|information|redacted_reasoning|think|/think|/search|/information)'
                next_tag_match = re.search(next_tag_pattern, remaining_text, re.IGNORECASE)
                if next_tag_match:
                    answer = remaining_text[:next_tag_match.start()].strip()
                else:
                    # 没有找到下一个标签，提取到文本末尾
                    # 但限制长度，避免提取过多内容
                    answer = remaining_text.strip()
                    # 如果答案太长，尝试找到第一个句号、换行或合理断点
                    if len(answer) > 200:
                        # 查找第一个句号、换行或逗号后的合理断点
                        break_points = [
                            answer.find('.'),
                            answer.find('。'),
                            answer.find('\n'),
                            answer.find(','),
                            answer.find('，'),
                        ]
                        break_points = [bp for bp in break_points if bp > 0]
                        if break_points:
                            answer = answer[:min(break_points)].strip()
                        else:
                            answer = answer[:200].strip()
            
            if answer:
                cleaned = _clean_answer(answer)
                # CRITICAL: 最终验证，拒绝无意义单词
                if cleaned.lower().strip() in ['and', 'or', 'the', 'a', 'an']:
                    return None
                # 验证答案不是无意义的单词
                if is_valid_answer(cleaned):
                    return cleaned
    
    return None


def is_valid_answer(answer: str) -> bool:
    """
    验证答案是否有效（不是无意义的单词）
    """
    if not answer or len(answer.strip()) == 0:
        return False
    
    # 移除所有标点和空格后检查
    cleaned = re.sub(r'[^\w\u4e00-\u9fff]', '', answer.lower())
    
    # 如果是单个无意义单词，拒绝
    if cleaned in MEANINGLESS_WORDS:
        return False
    
    # 如果答案太短（少于2个字符）且是常见单词，拒绝
    if len(cleaned) < 2:
        return False
    
    # 如果答案只包含无意义单词的组合（如 "and the"），拒绝
    words = re.findall(r'\b\w+\b', answer.lower())
    if len(words) <= 2 and all(word in MEANINGLESS_WORDS for word in words):
        return False
    
    return True


def _clean_answer(answer: str) -> str:
    """
    清理答案：移除多余的空格、标点和换行
    """
    # 移除首尾空白
    answer = answer.strip()
    
    # 移除开头的冒号、破折号等
    answer = re.sub(r'^[：:\-\s]+', '', answer)
    
    # 移除结尾的标点（但保留必要的标点如句号）
    answer = re.sub(r'[：:\-\s]+$', '', answer)
    
    # 移除多余的换行和空格
    answer = re.sub(r'\s+', ' ', answer)
    
    # 如果答案仍然很长，只取第一句
    if len(answer) > 150:
        # 查找第一个句号（中英文）
        first_period = min(
            answer.find('.') if answer.find('.') > 0 else len(answer),
            answer.find('。') if answer.find('。') > 0 else len(answer),
            answer.find('\n') if answer.find('\n') > 0 else len(answer)
        )
        if first_period < len(answer) and first_period > 0:
            answer = answer[:first_period].strip()
        else:
            # 如果没有句号，取前100个字符
            answer = answer[:100].strip()
    
    return answer


def extract_r1_answer_from_prompt(prompt: str, begin_token: str = "<answer>", end_token: str = "</answer>") -> Optional[str]:
    """
    DEPRECATED: 此函数不应再使用，因为它可能从 prompt 指令中提取答案
    请直接使用 extract_r1_answer() 从 raw_pred 中提取
    
    从完整的 prompt 中提取答案（包括历史对话）
    优先从最后一段输出中提取，避免从 prompt 指令中提取
    """
    if not prompt:
        return None
    
    # 策略：只从 assistant 的输出部分提取，避免从 user prompt 的指令中提取
    # 查找最后一个 <|im_start|>assistant 或类似的标记，只从那里之后提取
    assistant_markers = [
        '<|im_start|>assistant',
        '<|assistant|>',
        'assistant:',
        'Assistant:'
    ]
    
    # 找到最后一个 assistant 标记的位置
    last_assistant_pos = -1
    for marker in assistant_markers:
        pos = prompt.rfind(marker)
        if pos > last_assistant_pos:
            last_assistant_pos = pos
    
    # 如果找到了 assistant 标记，只从那里之后提取
    if last_assistant_pos != -1:
        assistant_output = prompt[last_assistant_pos:]
        
        # 进一步检查：确保 <answer> 不在 user prompt 的指令中
        # 查找最后一个 user 标记
        user_markers = [
            '<|im_start|>user',
            '<|user|>',
            'user:',
            'User:'
        ]
        last_user_pos = -1
        for marker in user_markers:
            pos = prompt.rfind(marker, 0, last_assistant_pos)
            if pos > last_user_pos:
                last_user_pos = pos
        
        # 如果找到了 user 标记，检查 <answer> 是否在 user 部分
        if last_user_pos != -1:
            user_section = prompt[last_user_pos:last_assistant_pos]
            # 如果 user 部分包含 <answer>，说明是指令，不应该提取
            if begin_token.lower() in user_section.lower():
                # 检查是否是 "inside <answer> and </answer>" 这样的指令
                if re.search(r'(?:inside|output|provide|put|place).*?<answer>.*?and.*?</answer>', user_section, re.IGNORECASE):
                    return None  # 这是指令，不提取
        
        # 尝试从 assistant 输出中提取
        answer = extract_r1_answer(assistant_output, begin_token, end_token)
        if answer:
            # 最终验证：如果是无意义单词，拒绝
            if answer.lower().strip() in ['and', 'or', 'the', 'a', 'an']:
                return None
            return answer
    
    # 如果没有找到 assistant 标记，不提取（避免从 user prompt 中提取）
    return None

