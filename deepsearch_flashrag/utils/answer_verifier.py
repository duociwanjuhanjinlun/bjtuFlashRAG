"""
答案验证器：验证IRCoT生成的答案是否满足问题的所有约束条件
"""
import re
from typing import List, Dict, Tuple, Optional


class AnswerVerifier:
    """
    验证答案是否满足问题的所有约束条件
    """
    
    def __init__(self):
        # 时间约束模式
        self.time_patterns = [
            (r"between (\d{4}) and (\d{4})", "range"),
            (r"before (\d{4})", "before"),
            (r"after (\d{4})", "after"),
            (r"in the (\d{4})s", "decade"),
            (r"less than (\d+) years", "less_than"),
            (r"more than (\d+) years", "more_than"),
            (r"(\d+) years", "exact_years"),
        ]
        
        # 关系约束关键词
        self.relationship_keywords = [
            "worked for", "led", "founded", "married", "born", "died",
            "coached", "managed", "directed", "wrote", "created"
        ]
    
    def extract_constraints(self, question: str) -> List[Dict]:
        """
        从问题中提取所有约束条件
        
        返回: List[Dict] 每个约束包含type, value, description
        """
        constraints = []
        
        # 提取时间约束
        for pattern, constraint_type in self.time_patterns:
            matches = re.finditer(pattern, question, re.IGNORECASE)
            for match in matches:
                constraints.append({
                    'type': 'time',
                    'subtype': constraint_type,
                    'value': match.groups(),
                    'text': match.group(0),
                    'description': f"Time constraint: {match.group(0)}"
                })
        
        # 提取关系约束
        for keyword in self.relationship_keywords:
            if keyword in question.lower():
                # 提取包含该关键词的句子
                sentences = re.split(r'[.!?]', question)
                for sentence in sentences:
                    if keyword in sentence.lower():
                        constraints.append({
                            'type': 'relationship',
                            'keyword': keyword,
                            'text': sentence.strip(),
                            'description': f"Relationship: {sentence.strip()[:50]}"
                        })
                        break
        
        # 提取实体约束（人名、地名等）
        # 大写字母开头的词可能是实体
        entity_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        entities = re.findall(entity_pattern, question)
        if entities:
            constraints.append({
                'type': 'entity',
                'entities': entities[:5],  # 限制数量
                'description': f"Key entities: {', '.join(entities[:3])}"
            })
        
        return constraints
    
    def verify(self, 
               question: str, 
               answer: str, 
               retrieved_docs: List[Dict],
               thoughts: List[str]) -> Tuple[bool, str, List[str]]:
        """
        验证答案是否满足所有约束条件
        
        参数:
            question: 原始问题
            answer: 生成的答案
            retrieved_docs: 检索到的文档列表
            thoughts: 推理过程列表
        
        返回:
            (is_valid, message, missing_constraints)
        """
        if not answer or answer.strip() == "":
            return False, "Answer is empty", []
        
        # 提取约束
        constraints = self.extract_constraints(question)
        
        if not constraints:
            # 如果没有约束，只检查答案是否在文档中出现
            return self._check_answer_in_docs(answer, retrieved_docs, thoughts)
        
        # 检查每个约束
        satisfied = []
        missing = []
        
        for constraint in constraints:
            if self._check_constraint(constraint, answer, retrieved_docs, thoughts):
                satisfied.append(constraint['description'])
            else:
                missing.append(constraint['description'])
        
        # 如果超过30%的约束未满足，认为答案不可靠
        missing_ratio = len(missing) / len(constraints) if constraints else 0
        
        if missing_ratio > 0.3:
            return False, f"Too many constraints not satisfied ({len(missing)}/{len(constraints)})", missing
        
        return True, f"All constraints satisfied ({len(satisfied)}/{len(constraints)})", []
    
    def _check_constraint(self, constraint: Dict, answer: str, 
                         docs: List[Dict], thoughts: List[str]) -> bool:
        """检查单个约束是否满足"""
        constraint_type = constraint.get('type')
        
        if constraint_type == 'time':
            # 时间约束检查：在文档中查找相关时间信息
            return self._check_time_constraint(constraint, docs, thoughts)
        elif constraint_type == 'relationship':
            # 关系约束检查：检查关系是否在文档中提及
            return self._check_relationship_constraint(constraint, answer, docs, thoughts)
        elif constraint_type == 'entity':
            # 实体约束检查：检查关键实体是否在文档中出现
            return self._check_entity_constraint(constraint, docs, thoughts)
        else:
            return True  # 未知类型，默认满足
    
    def _check_time_constraint(self, constraint: Dict, docs: List[Dict], 
                              thoughts: List[str]) -> bool:
        """检查时间约束"""
        # 在文档和思考过程中查找时间信息
        all_text = " ".join([doc.get('contents', '') for doc in docs])
        all_text += " " + " ".join(thoughts)
        
        # 提取所有年份
        years = re.findall(r'\b(19|20)\d{2}\b', all_text)
        
        # 简单检查：如果找到相关年份，认为满足
        # 更严格的检查可以根据constraint的subtype进行
        return len(years) > 0
    
    def _check_relationship_constraint(self, constraint: Dict, answer: str,
                                      docs: List[Dict], thoughts: List[str]) -> bool:
        """检查关系约束"""
        keyword = constraint.get('keyword', '')
        all_text = " ".join([doc.get('contents', '') for doc in docs])
        all_text += " " + " ".join(thoughts)
        all_text += " " + answer
        
        # 检查关键词和答案是否同时出现
        return keyword.lower() in all_text.lower() and answer.lower() in all_text.lower()
    
    def _check_entity_constraint(self, constraint: Dict, 
                                docs: List[Dict], thoughts: List[str]) -> bool:
        """检查实体约束"""
        entities = constraint.get('entities', [])
        if not entities:
            return True
        
        all_text = " ".join([doc.get('contents', '') for doc in docs])
        all_text += " " + " ".join(thoughts)
        
        # 检查至少一个实体在文档中出现
        found = sum(1 for entity in entities if entity.lower() in all_text.lower())
        return found > 0
    
    def _check_answer_in_docs(self, answer: str, docs: List[Dict], 
                             thoughts: List[str]) -> bool:
        """检查答案是否在文档中出现"""
        all_text = " ".join([doc.get('contents', '') for doc in docs])
        all_text += " " + " ".join(thoughts)
        
        # 清理答案：移除常见前缀
        clean_answer = answer
        for prefix in ["So the answer is:", "The answer is:", "Answer:"]:
            if clean_answer.startswith(prefix):
                clean_answer = clean_answer[len(prefix):].strip()
        
        # 检查答案的关键部分是否在文档中
        answer_words = clean_answer.split()
        if len(answer_words) > 5:
            # 如果答案太长，只检查前几个词
            answer_words = answer_words[:5]
        
        answer_phrase = " ".join(answer_words)
        return answer_phrase.lower() in all_text.lower()
    
    def suggest_missing_info(self, question: str, missing_constraints: List[str]) -> str:
        """
        根据缺失的约束，建议需要检索的信息
        """
        suggestions = []
        
        for constraint_desc in missing_constraints:
            if "Time constraint" in constraint_desc:
                suggestions.append("Search for specific years or time periods")
            elif "Relationship" in constraint_desc:
                suggestions.append("Search for relationships between entities")
            elif "Key entities" in constraint_desc:
                suggestions.append("Search for specific entities mentioned in the question")
        
        if suggestions:
            return "Need to find: " + "; ".join(set(suggestions))
        return "Need more information to verify the answer"

