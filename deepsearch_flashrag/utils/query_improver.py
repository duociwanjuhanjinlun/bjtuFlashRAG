"""
查询生成改进工具：从问题和当前思考中生成更具体的检索查询
实现功能：
1. 实体识别增强（NER + 规则）
2. 查询重写/扩展
3. 多查询策略
"""
import re
from typing import List, Optional, Dict, Tuple
from collections import Counter


class QueryImprover:
    """
    改进IRCoT生成的查询，使其更具体、更有效
    
    功能：
    1. 实体识别增强：使用规则和模式识别关键实体
    2. 查询重写：扩展查询，添加同义词和关联词
    3. 多查询策略：为复杂问题生成多个查询变体
    """
    
    def __init__(self, use_ner: bool = False):
        """
        初始化查询改进器
        
        Args:
            use_ner: 是否使用 NER 模型（如果可用）
        """
        self.use_ner = use_ner
        self.ner_model = None
        
        # 尝试加载 NER 模型（如果可用）
        if use_ner:
            try:
                import spacy
                try:
                    self.ner_model = spacy.load("en_core_web_sm")
                    print("Loaded spaCy NER model for entity recognition")
                except:
                    print("spaCy model not found, using rule-based entity recognition")
            except ImportError:
                print("spaCy not available, using rule-based entity recognition")
        
        # 增强的实体提取模式
        self.entity_patterns = [
            # 人名模式（首字母大写，可能包含多个词）
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b',
            # 地名模式（常见地名特征）
            r'\b([A-Z][a-z]+(?:\s+(?:City|State|Country|University|College|School|Stadium|Theater|Museum|Park)))\b',
            # 组织名模式
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Corporation|Company|Inc|Ltd|University|College|League|Association|Organization)))\b',
            # 作品名（引号或斜体）
            r'["\']([^"\']+)["\']',
            # 特定实体模式
            r'\b(the\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
        ]
        
        # 时间信息模式（增强）
        self.time_patterns = [
            r'\b(19|20)\d{2}\b',  # 年份
            r'\b(\d{4})s\b',  # 年代
            r'before\s+(\d{4})',
            r'after\s+(\d{4})',
            r'between\s+(\d{4})\s+and\s+(\d{4})',
            r'in\s+(\d{4})',
            r'during\s+the\s+(\d{4})s',
            r'early\s+(\d{4})s',
            r'late\s+(\d{4})s',
        ]
        
        # 关系关键词（扩展）
        self.relationship_keywords = [
            'coach', 'coached', 'manager', 'managed', 'director', 'directed',
            'president', 'founded', 'worked for', 'led', 'created', 'wrote',
            'played', 'starred', 'appeared', 'won', 'awarded', 'received',
            'born', 'died', 'graduated', 'attended', 'married', 'parent',
            'child', 'sibling', 'brother', 'sister', 'father', 'mother'
        ]
        
        # 同义词词典（用于查询扩展）
        self.synonyms = {
            'coach': ['manager', 'trainer', 'head coach'],
            'director': ['filmmaker', 'movie director'],
            'actor': ['actress', 'performer', 'star'],
            'award': ['prize', 'honor', 'recognition'],
            'movie': ['film', 'picture', 'motion picture'],
            'series': ['show', 'tv show', 'television series'],
            'team': ['club', 'squad'],
            'player': ['athlete', 'competitor'],
        }
        
        # 问题类型关键词
        self.question_type_keywords = {
            'person': ['who', 'person', 'individual', 'actor', 'director', 'coach', 'player'],
            'place': ['where', 'city', 'country', 'location', 'place'],
            'time': ['when', 'year', 'date', 'time'],
            'organization': ['company', 'organization', 'team', 'university', 'school'],
            'work': ['movie', 'film', 'book', 'song', 'album', 'series'],
        }
    
    def extract_entities(self, text: str, use_ner: bool = None) -> List[str]:
        """
        从文本中提取实体（增强版）
        
        Args:
            text: 输入文本
            use_ner: 是否使用 NER（None 时使用 self.use_ner）
        
        Returns:
            实体列表
        """
        entities = []
        
        # 方法1: 使用 NER 模型（如果可用）
        if (use_ner if use_ner is not None else self.use_ner) and self.ner_model:
            try:
                doc = self.ner_model(text)
                for ent in doc.ents:
                    if ent.label_ in ['PERSON', 'ORG', 'GPE', 'WORK_OF_ART', 'EVENT']:
                        entities.append(ent.text)
            except Exception as e:
                print(f"NER extraction failed: {e}, falling back to rule-based")
        
        # 方法2: 基于规则的实体提取
        for pattern in self.entity_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    entities.extend([m for m in match if m and m.strip()])
                else:
                    if match and match.strip():
                        entities.append(match)
        
        # 去重并过滤常见词
        common_words = {'The', 'This', 'That', 'There', 'They', 'These', 'Those', 
                       'Question', 'Answer', 'Search', 'Information', 'Need', 'Find'}
        entities = [e.strip() for e in set(entities) 
                    if e.strip() not in common_words and len(e.strip()) > 2]
        
        # 按长度和重要性排序（较长的实体通常更重要）
        entities = sorted(entities, key=lambda x: (len(x), x), reverse=True)
        
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
    
    def expand_query(self, query: str) -> str:
        """
        查询扩展：添加同义词和关联词
        
        Args:
            query: 原始查询
        
        Returns:
            扩展后的查询
        """
        words = query.lower().split()
        expanded_words = []
        
        for word in words:
            expanded_words.append(word)
            # 添加同义词
            if word in self.synonyms:
                expanded_words.extend(self.synonyms[word][:1])  # 只添加第一个同义词
        
        return ' '.join(expanded_words)
    
    def detect_question_type(self, question: str) -> str:
        """
        检测问题类型
        
        Returns:
            问题类型：'person', 'place', 'time', 'organization', 'work', 'other'
        """
        question_lower = question.lower()
        
        for qtype, keywords in self.question_type_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return qtype
        
        return 'other'
    
    def improve_query(self, question: str, current_thought: str = "", 
                     original_query: str = "") -> str:
        """
        改进查询，生成更具体的检索查询（增强版）
        
        参数:
            question: 原始问题
            current_thought: 当前的思考过程（可选）
            original_query: 模型生成的原始查询（可选）
        
        返回:
            改进后的查询字符串
        """
        # Clean inputs: remove XML/HTML tags
        import re
        question = re.sub(r'<[^>]+>', '', question).strip()
        current_thought = re.sub(r'<[^>]+>', '', current_thought).strip() if current_thought else ""
        original_query = re.sub(r'<[^>]+>', '', original_query).strip() if original_query else ""
        """
        改进查询，生成更具体的检索查询（增强版）
        
        参数:
            question: 原始问题
            current_thought: 当前的思考过程（可选）
            original_query: 模型生成的原始查询（可选）
        
        返回:
            改进后的查询字符串
        """
        # 1. 从问题中提取关键信息
        question_entities = self.extract_entities(question)
        question_time = self.extract_time_info(question)
        question_relationships = self.extract_relationships(question)
        question_type = self.detect_question_type(question)
        
        # 2. 从当前思考中提取关键信息（如果有）
        if current_thought:
            thought_entities = self.extract_entities(current_thought)
            thought_time = self.extract_time_info(current_thought)
            thought_relationships = self.extract_relationships(current_thought)
        else:
            thought_entities = []
            thought_time = None
            thought_relationships = []
        
        # 3. 从原始查询中提取信息（如果有）
        if original_query:
            query_entities = self.extract_entities(original_query)
            query_time = self.extract_time_info(original_query)
        else:
            query_entities = []
            query_time = None
        
        # 4. 合并信息（优先级：问题 > 思考 > 原始查询）
        all_entities = list(dict.fromkeys(question_entities + thought_entities + query_entities))[:5]
        time_info = question_time or thought_time or query_time
        all_relationships = list(dict.fromkeys(question_relationships + thought_relationships))
        
        # 5. 构建查询
        query_parts = []
        
        # 优先添加最重要的实体（通常是答案相关的）
        if all_entities:
            # 根据问题类型选择实体
            if question_type == 'person' and all_entities:
                # 对于人物问题，优先包含人名
                person_entities = [e for e in all_entities if len(e.split()) >= 2]
                if person_entities:
                    query_parts.extend(person_entities[:2])
                else:
                    query_parts.extend(all_entities[:2])
            else:
                query_parts.extend(all_entities[:3])  # 最多3个实体
        
        # 添加关系（帮助定位）
        if all_relationships:
            query_parts.extend(all_relationships[:2])  # 最多2个关系
        
        # 添加时间信息
        if time_info:
            query_parts.append(time_info)
        
        # 6. 如果查询太短，从原始查询或思考中补充
        if len(' '.join(query_parts)) < 15:
            # 从原始查询中提取关键词
            if original_query:
                # 提取原始查询中的关键词（去除停用词）
                stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
                query_words = [w for w in original_query.split() 
                             if w.lower() not in stop_words and len(w) > 3]
                if query_words:
                    query_parts.extend(query_words[:3])
            elif current_thought:
                # 从思考中提取关键短语
                thought_words = current_thought.split()
                important_words = [w for w in thought_words 
                                 if len(w) > 4 and w.lower() not in 
                                 ['need', 'find', 'search', 'information', 'about', 'question', 'think', 'should']]
                if important_words:
                    query_parts.extend(important_words[:3])
        
        # 7. 组合查询
        improved_query = ' '.join(query_parts)
        
        # 8. 查询扩展（添加同义词）
        if len(improved_query.strip()) > 5:
            improved_query = self.expand_query(improved_query)
        
        # 9. 如果改进后的查询太短或为空，使用原始查询或思考
        if len(improved_query.strip()) < 5:
            if original_query:
                improved_query = original_query.strip()
            elif current_thought:
                improved_query = current_thought.strip()
            else:
                improved_query = question.strip()
            
            # 如果太长，只取前50个词
            words = improved_query.split()
            if len(words) > 50:
                improved_query = ' '.join(words[:50])
        
        return improved_query.strip()
    
    def generate_multiple_queries(self, question: str, current_thought: str = "", 
                                  original_query: str = "", num_queries: int = 2) -> List[str]:
        """
        生成多个查询变体（用于查询扩展和多查询策略）
        
        Args:
            question: 原始问题
            current_thought: 当前思考过程
            original_query: 模型生成的原始查询
            num_queries: 需要生成的查询数量
        
        Returns:
            查询列表
        """
        queries = []
        combined_text = f"{question} {current_thought} {original_query}".strip()
        
        # 主查询（完整优化版）
        main_query = self.improve_query(question, current_thought, original_query)
        queries.append(main_query)
        
        # 如果只需要一个查询，直接返回
        if num_queries == 1:
            return queries
        
        # 变体1: 只使用实体（更精确）
        entities = self.extract_entities(combined_text)
        if entities:
            entity_query = ' '.join(entities[:4])  # 使用更多实体
            if entity_query and entity_query != main_query and len(entity_query) > 5:
                queries.append(entity_query)
        
        # 变体2: 实体 + 时间（时间相关查询）
        time_info = self.extract_time_info(combined_text)
        if time_info:
            if entities:
                time_entity_query = ' '.join(entities[:2] + [time_info])
            else:
                time_entity_query = f"{main_query} {time_info}"
            
            if time_entity_query not in queries and len(time_entity_query) > 5:
                queries.append(time_entity_query)
        
        # 变体3: 关系 + 实体（关系查询）
        relationships = self.extract_relationships(combined_text)
        if relationships and entities:
            relation_query = ' '.join(relationships[:2] + entities[:2])
            if relation_query not in queries and len(relation_query) > 5:
                queries.append(relation_query)
        
        # 变体4: 基于问题类型生成特定查询
        question_type = self.detect_question_type(question)
        if question_type != 'other' and entities:
            type_specific_query = ' '.join(entities[:3])
            if type_specific_query not in queries:
                queries.append(type_specific_query)
        
        # 变体5: 简化版（只保留核心关键词）
        if len(queries) < num_queries and main_query:
            # 提取核心词（去除停用词和短词）
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            core_words = [w for w in main_query.split() 
                         if w.lower() not in stop_words and len(w) > 3]
            if len(core_words) >= 3:
                simplified_query = ' '.join(core_words[:5])
                if simplified_query not in queries:
                    queries.append(simplified_query)
        
        # 去重并限制数量
        seen = set()
        unique_queries = []
        for q in queries:
            q_lower = q.lower()
            if q_lower not in seen and len(q.strip()) > 5:
                seen.add(q_lower)
                unique_queries.append(q)
        
        return unique_queries[:num_queries]

