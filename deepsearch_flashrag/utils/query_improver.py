"""
查询生成改进工具：从问题和当前思考中生成更具体的检索查询
"""
import re
from typing import List, Optional


class QueryImprover:
    """
    改进IRCoT生成的查询，使其更具体、更有效
    """
    
    def __init__(self):
        # 实体提取模式
        self.entity_patterns = [
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # 大写开头的词（可能是人名、地名）
            r'\b(the\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',  # "the + 大写"（可能是组织名）
        ]
        
        # 时间信息模式
        self.time_patterns = [
            r'\b(19|20)\d{2}\b',  # 年份
            r'\b(\d{4})s\b',  # 年代
            r'before\s+(\d{4})',
            r'after\s+(\d{4})',
            r'between\s+(\d{4})\s+and\s+(\d{4})',
        ]
        
        # 关系关键词
        self.relationship_keywords = [
            'coach', 'coached', 'manager', 'managed', 'director', 'directed',
            'president', 'founded', 'worked for', 'led', 'created', 'wrote'
        ]
    
    def extract_entities(self, text: str) -> List[str]:
        """从文本中提取实体"""
        entities = []
        
        for pattern in self.entity_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    entities.extend([m for m in match if m])
                else:
                    entities.append(match)
        
        # 去重并过滤常见词
        common_words = {'The', 'This', 'That', 'There', 'They', 'These', 'Those'}
        entities = [e for e in set(entities) if e not in common_words and len(e) > 2]
        
        return entities[:10]  # 限制数量
    
    def extract_time_info(self, text: str) -> Optional[str]:
        """从文本中提取时间信息"""
        for pattern in self.time_patterns:
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], tuple):
                    return ' '.join([str(m) for m in matches[0] if m])
                else:
                    return str(matches[0])
        return None
    
    def extract_relationships(self, text: str) -> List[str]:
        """从文本中提取关系关键词"""
        found = []
        text_lower = text.lower()
        for keyword in self.relationship_keywords:
            if keyword in text_lower:
                found.append(keyword)
        return found
    
    def improve_query(self, question: str, current_thought: str) -> str:
        """
        改进查询，生成更具体的检索查询
        
        参数:
            question: 原始问题
            current_thought: 当前的思考过程
        
        返回:
            改进后的查询字符串
        """
        # 1. 从问题中提取关键信息
        question_entities = self.extract_entities(question)
        question_time = self.extract_time_info(question)
        question_relationships = self.extract_relationships(question)
        
        # 2. 从当前思考中提取关键信息
        thought_entities = self.extract_entities(current_thought)
        thought_time = self.extract_time_info(current_thought)
        thought_relationships = self.extract_relationships(current_thought)
        
        # 3. 合并信息（优先使用问题中的信息）
        all_entities = list(dict.fromkeys(question_entities + thought_entities))[:5]  # 去重并限制
        time_info = question_time or thought_time
        all_relationships = list(dict.fromkeys(question_relationships + thought_relationships))
        
        # 4. 构建查询
        query_parts = []
        
        # 添加实体
        if all_entities:
            query_parts.extend(all_entities[:3])  # 最多3个实体
        
        # 添加关系
        if all_relationships:
            query_parts.extend(all_relationships[:2])  # 最多2个关系
        
        # 添加时间信息
        if time_info:
            query_parts.append(time_info)
        
        # 如果查询太短，使用原始思考的一部分
        if len(' '.join(query_parts)) < 10:
            # 从思考中提取关键短语（去除常见词）
            thought_words = current_thought.split()
            important_words = [w for w in thought_words 
                             if len(w) > 4 and w.lower() not in 
                             ['need', 'find', 'search', 'information', 'about', 'question', 'think']]
            if important_words:
                query_parts.extend(important_words[:3])
        
        # 5. 组合查询
        improved_query = ' '.join(query_parts)
        
        # 如果改进后的查询太短或为空，使用原始思考
        if len(improved_query.strip()) < 5:
            # 使用原始思考，但清理一下
            improved_query = current_thought.strip()
            # 如果太长，只取前50个词
            words = improved_query.split()
            if len(words) > 50:
                improved_query = ' '.join(words[:50])
        
        return improved_query.strip()
    
    def generate_multiple_queries(self, question: str, current_thought: str, 
                                  num_queries: int = 2) -> List[str]:
        """
        生成多个查询变体（用于查询扩展）
        """
        queries = []
        
        # 主查询
        main_query = self.improve_query(question, current_thought)
        queries.append(main_query)
        
        # 如果只需要一个查询，直接返回
        if num_queries == 1:
            return queries
        
        # 生成变体：只使用实体
        entities = self.extract_entities(question + " " + current_thought)
        if entities:
            entity_query = ' '.join(entities[:3])
            if entity_query != main_query:
                queries.append(entity_query)
        
        # 生成变体：实体 + 时间
        time_info = self.extract_time_info(question + " " + current_thought)
        if time_info and entities:
            time_entity_query = ' '.join(entities[:2] + [time_info])
            if time_entity_query not in queries:
                queries.append(time_entity_query)
        
        return queries[:num_queries]

