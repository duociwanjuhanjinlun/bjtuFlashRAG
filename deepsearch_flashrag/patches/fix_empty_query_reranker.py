"""
修复reranker处理空查询的问题
在BiReranker的get_rerank_scores方法中过滤空查询
"""
import numpy as np


def patch_bireranker_get_rerank_scores(original_method):
    """
    包装BiReranker.get_rerank_scores方法，过滤空查询
    """
    def patched_get_rerank_scores(self, query_list, doc_list, batch_size):
        # 过滤空查询，用占位符替换
        processed_query_list = []
        query_mapping = []  # 记录原始索引到处理后的索引的映射
        
        for idx, query in enumerate(query_list):
            if query and query.strip():  # 非空查询
                processed_query_list.append(query)
                query_mapping.append(len(processed_query_list) - 1)
            else:
                # 空查询用占位符替换
                processed_query_list.append(" ")  # 使用单个空格作为占位符
                query_mapping.append(len(processed_query_list) - 1)
        
        # 使用处理后的查询列表
        query_emb = []
        for start_idx in range(0, len(processed_query_list), batch_size):
            query_batch = processed_query_list[start_idx : start_idx + batch_size]
            # 过滤掉空字符串
            valid_queries = [q if q.strip() else " " for q in query_batch]
            batch_emb = self.encoder.encode(valid_queries, is_query=True)
            query_emb.append(batch_emb)
        query_emb = np.concatenate(query_emb, axis=0)

        flat_doc_list = sum(doc_list, [])
        doc_emb = []
        for start_idx in range(0, len(flat_doc_list), batch_size):
            doc_batch = flat_doc_list[start_idx : start_idx + batch_size]
            batch_emb = self.encoder.encode(doc_batch, is_query=False)
            doc_emb.append(batch_emb)
        doc_emb = np.concatenate(doc_emb, axis=0)

        scores = query_emb @ doc_emb.T  # K*L
        all_scores = []
        score_idx = 0
        for idx, doc in enumerate(doc_list):
            all_scores.extend(scores[idx, score_idx : score_idx + len(doc)])
            score_idx += len(doc)

        return all_scores
    
    return patched_get_rerank_scores

