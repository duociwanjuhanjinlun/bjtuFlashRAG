#!/usr/bin/env python
"""
运行 SearchR1 Pipeline (集成 Refiner)
"""
import argparse
import sys
import copy
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm

# 添加项目路径
script_file = Path(__file__).resolve()
script_dir = script_file.parent
project_root = script_dir.parent
parent_dir = project_root.parent
parent_dir_str = str(parent_dir.resolve())
if parent_dir_str not in sys.path:
    sys.path.insert(0, parent_dir_str)

from flashrag.config import Config
from flashrag.utils import get_dataset, get_retriever, get_generator
from flashrag.dataset import Dataset
from flashrag.pipeline.reasoning_pipeline import SearchR1Pipeline
from flashrag.refiner.selective_context_compressor import SelectiveContext
from flashrag.utils.utils import extract_between
from deepsearch_flashrag.prompts.r1_concise_prompt import ConciseSearchR1PromptTemplate
from deepsearch_flashrag.utils.r1_answer_extractor import extract_r1_answer, extract_r1_answer_from_prompt, is_valid_answer
from deepsearch_flashrag.utils.query_improver import QueryImprover

class RefinedSearchR1Pipeline(SearchR1Pipeline):
    """
    集成 Selective Context Refiner 的 SearchR1Pipeline
    同时修复了 search token 解析过于严格导致无法触发检索的问题
    """
    def __init__(self, config, prompt_template=None):
        super().__init__(config, prompt_template)
        
        self.use_refiner = config['use_refiner'] if 'use_refiner' in config else False
        self.refiner_name = config['refiner_name'] if 'refiner_name' in config else None
        self.refiner = None
        
        if self.use_refiner and self.refiner_name == "selective-context":
            print("Initializing Selective Context Refiner...")
            model_path = config['refiner_model_path'] if 'refiner_model_path' in config else "gpt2"
            try:
                self.refiner = SelectiveContext(model_type="gpt2", model_path=model_path, lang="en")
                self.refiner_config = config['refiner_config'] if 'refiner_config' in config else {"reduce_ratio": 0.2}
                print(f"Refiner initialized with config: {self.refiner_config}")
            except Exception as e:
                print(f"Warning: Failed to initialize refiner: {e}")
                self.use_refiner = False
        
        # Initialize query improver if enabled
        if 'query_improver_config' in config:
            query_improver_config = config['query_improver_config']
            enabled = query_improver_config.get('enabled', True) if isinstance(query_improver_config, dict) else True
        else:
            query_improver_config = {}
            enabled = True  # 默认启用
        
        if enabled:
            try:
                use_ner = query_improver_config.get('use_ner', False) if isinstance(query_improver_config, dict) else False
                multi_query = query_improver_config.get('multi_query', False) if isinstance(query_improver_config, dict) else False
                multi_query_num = query_improver_config.get('multi_query_num', 2) if isinstance(query_improver_config, dict) else 2
                
                self.query_improver = QueryImprover(use_ner=use_ner)
                self.use_query_improver = True
                self.multi_query_strategy = multi_query
                self.multi_query_num = multi_query_num
                print(f"Query Improver initialized: multi_query={self.multi_query_strategy}, num={self.multi_query_num}")
            except Exception as e:
                print(f"Warning: Failed to initialize query improver: {e}")
                self.query_improver = None
                self.use_query_improver = False
                self.multi_query_strategy = False
        else:
            self.query_improver = None
            self.use_query_improver = False
            self.multi_query_strategy = False

    def _retrieved_docs_to_string(self, retrieved_docs: List[Dict]):
        format_doc_string = ""
        for idx, doc in enumerate(retrieved_docs):
            contents = doc['contents']
            title = contents.split('\n')[0]
            text = '\n'.join(contents.split('\n')[1:])
            
            # Apply Refiner
            if self.use_refiner and self.refiner:
                try:
                    # Selective Context returns (context, masked_sents)
                    refined_text, _ = self.refiner(text, **self.refiner_config)
                    text = refined_text
                except Exception as e:
                    print(f"Error during refinement: {e}")
            
            format_doc_string += f"Doc {idx+1}(Title: {title}) {text}\n"
            
        format_doc_string = f'\n\n{self.begin_of_documents_token}\n{format_doc_string}\n{self.end_of_documents_token}\n\n'
        return format_doc_string

    def run(self, dataset, do_eval=True, pred_process_fun=None):
        """
        Override run method to fix search token parsing
        """
        prompts = [self.prompt_template.get_string(question=question) for question in dataset.question]
        dataset.update_output('prompt', prompts)
        dataset.update_output('finish_flag', [False] * len(prompts))
        dataset.update_output('retrieval_results', [{} for _ in range(len(prompts))])
        dataset.update_output('retrieved_times', [0] * len(prompts))
        dataset.update_output('raw_pred', [''] * len(prompts))  # Initialize raw_pred for all items
        dataset.update_output('max_raw_pred_length', [0] * len(prompts))  # Track max length to detect loops

        # Logic of reasoning
        for current_step_idx in range(self.max_retrieval_num + 1):
            exist_items = [item for item in dataset if item.finish_flag == False]
            exist_prompts = [item.prompt for item in exist_items]
            
            print(f"Current step: {current_step_idx}, exist_items: {len(exist_items)}")

            if len(exist_items) == 0:
                print("All prompts are finished")
                break
            if current_step_idx == self.max_retrieval_num:
                print("Max retrieval number reached")
                for item in exist_items:
                    item.pred = 'No valid answer found'
                    item.finish_flag = True
                    item.finish_reason = 'Reach max retrieval number'
                break

            # Generate with increased max_tokens to ensure complete output
            # Pass max_tokens explicitly to ensure model has enough space to output complete <answer> tags
            # Note: max_tokens here refers to the maximum number of NEW tokens to generate (not total)
            generation_params_override = {
                'max_new_tokens': 2048,  # Ensure enough tokens for complete answer (explicit new tokens)
            }
            step_outputs = self.generator.generate(exist_prompts, stop=self.stop_tokens, **generation_params_override)
            step_query_list = [] # store generated queries for retrieval

            # parse each sample's step output
            for item, step_output in zip(exist_items, step_outputs):
                # Save raw output for analysis
                raw_output = step_output.strip()
                item.prompt = item.prompt + raw_output
                
                # Save raw_pred for debugging and analysis (accumulate across steps)
                # Get existing raw_pred if any, and append new output
                try:
                    existing_raw = item.raw_pred if hasattr(item, 'raw_pred') else ''
                except:
                    existing_raw = ''
                
                if existing_raw:
                    new_raw = existing_raw + raw_output
                else:
                    new_raw = raw_output
                item.update_output('raw_pred', new_raw)
                
                # Track max length to detect potential infinite loops
                current_max = getattr(item, 'max_raw_pred_length', 0)
                if len(new_raw) > current_max:
                    item.update_output('max_raw_pred_length', len(new_raw))
                
                # Safety: If raw_pred becomes too long (>20000 chars), force stop to prevent infinite loops
                if len(new_raw) > 20000:
                    print(f"WARNING: Item {item.id} raw_pred exceeds 20000 chars, forcing stop to prevent infinite loop")
                    item.pred = 'No valid answer found (output too long, possible infinite loop)'
                    item.finish_flag = True
                    item.finish_reason = 'Output length limit exceeded'
                    continue  # Skip further processing for this item
                
                # Get accumulated raw_pred (all model outputs so far) - this is the ACTUAL model output
                accumulated_raw = new_raw  # Use the just-updated raw_pred
                
                # DEBUG: Log raw_pred length to diagnose truncation issues
                if len(accumulated_raw) < 200 and '<search>' in accumulated_raw.lower() and '</search>' not in accumulated_raw:
                    print(f"DEBUG: Item {item.id} has truncated raw_pred ({len(accumulated_raw)} chars, missing </search>): {accumulated_raw[-100:]}")
                
                # DEBUG: Detect potential infinite loops (repetitive content)
                if len(accumulated_raw) > 5000:
                    # Check for repetitive patterns
                    last_500 = accumulated_raw[-500:]
                    first_500 = accumulated_raw[:500] if len(accumulated_raw) > 500 else accumulated_raw
                    if last_500 == first_500:
                        print(f"WARNING: Item {item.id} may be in a loop - last 500 chars match first 500 chars")
                    # Check for excessive repetition of same phrase
                    words = accumulated_raw.split()
                    if len(words) > 100:
                        from collections import Counter
                        word_freq = Counter(words)
                        most_common = word_freq.most_common(5)
                        if most_common[0][1] > len(words) * 0.3:  # Same word appears >30% of the time
                            print(f"WARNING: Item {item.id} may be stuck - word '{most_common[0][0]}' appears {most_common[0][1]} times in {len(words)} words")
                
                # Check for Answer (CRITICAL: Only extract from actual model output, NEVER from prompt instructions)
                # STRICT RULE: Only extract if raw_pred (accumulated model output) contains <answer> tag
                answer = None
                
                # CRITICAL: Only extract if raw_pred actually contains <answer> tag
                # This ensures we NEVER extract from prompt instructions
                if self.begin_of_answer_token.lower() in accumulated_raw.lower():
                    # Extract from raw_pred (actual model output), not from full prompt
                    answer = extract_r1_answer(accumulated_raw, self.begin_of_answer_token, self.end_of_answer_token)
                    
                    # DOUBLE CHECK: If answer is a meaningless word like "and", reject it
                    if answer and answer.lower().strip() in ['and', 'or', 'the', 'a', 'an']:
                        answer = None
                        print(f"WARNING: Rejected meaningless answer '{answer}' for item {item.id}")
                
                if answer is not None:
                    item.pred = answer
                    item.finish_flag = True
                    item.finish_reason = "Finished"
                
                # Check for Search Query (Relaxed Check)
                elif self.begin_of_query_token in step_output:
                    # If the output contains <search> but not </search>, it's likely the stop token stripped it
                    # OR the model didn't finish. We assume it's a query.
                    if self.end_of_query_token not in step_output:
                        step_output_for_extraction = step_output + self.end_of_query_token
                    else:
                        step_output_for_extraction = step_output

                    query = extract_between(step_output_for_extraction, self.begin_of_query_token, self.end_of_query_token)
                    if query is not None:
                        # Clean query: remove any XML/HTML tags and extra whitespace
                        import re
                        query = re.sub(r'<[^>]+>', '', query)  # Remove all tags
                        query = ' '.join(query.split())  # Normalize whitespace
                        
                        # Query improvement: 使用 QueryImprover 改进查询
                        if self.use_query_improver and self.query_improver and query.strip():
                            try:
                                # 提取当前思考过程（从 raw_pred 中提取 <think> 部分）
                                current_thought = ""
                                if hasattr(item, 'raw_pred') and item.raw_pred:
                                    reasoning_match = re.search(
                                        r'<think>(.*?)</think>',
                                        item.raw_pred,
                                        re.DOTALL | re.IGNORECASE
                                    )
                                    if not reasoning_match:
                                        # Try alternative tag
                                        reasoning_match = re.search(
                                            r'<think>(.*?)</think>',
                                            item.raw_pred,
                                            re.DOTALL | re.IGNORECASE
                                        )
                                    if reasoning_match:
                                        current_thought = reasoning_match.group(1).strip()
                                        # Clean reasoning text too
                                        current_thought = re.sub(r'<[^>]+>', '', current_thought)
                                        current_thought = ' '.join(current_thought.split())
                                
                                # 改进查询
                                if self.multi_query_strategy:
                                    # 多查询策略：生成多个查询变体
                                    improved_queries = self.query_improver.generate_multiple_queries(
                                        question=item.question,
                                        current_thought=current_thought,
                                        original_query=query,
                                        num_queries=self.multi_query_num
                                    )
                                    # 为每个查询变体创建检索任务
                                    for improved_query in improved_queries:
                                        if improved_query and improved_query.strip():
                                            step_query_list.append({
                                                'item': item,
                                                'query': improved_query,
                                                'original_query': query  # 保存原始查询用于日志
                                            })
                                else:
                                    # 单查询策略：只改进原始查询
                                    improved_query = self.query_improver.improve_query(
                                        question=item.question,
                                        current_thought=current_thought,
                                        original_query=query
                                    )
                                    if improved_query and improved_query.strip():
                                        step_query_list.append({
                                            'item': item,
                                            'query': improved_query,
                                            'original_query': query  # 保存原始查询用于日志
                                        })
                                    else:
                                        # 如果改进失败，使用原始查询
                                        step_query_list.append({'item': item, 'query': query})
                            except Exception as e:
                                print(f"WARNING: Query improvement failed for item {item.id}: {e}")
                                # 如果改进失败，使用原始查询
                                step_query_list.append({'item': item, 'query': query})
                        else:
                            # 不使用查询改进，直接使用原始查询
                            step_query_list.append({'item': item, 'query': query})
                    else:
                        # Fallback if extraction fails
                        item.pred = 'No valid answer found'
                        item.finish_flag = True
                        item.finish_reason = 'Query instruction error'

                else:
                    # No answer and no search query found
                    # CRITICAL: Only check raw_pred (actual model output), NEVER check full prompt
                    answer = None
                    
                    # Get accumulated raw_pred (use the one we just updated)
                    try:
                        accumulated_raw = item.raw_pred if hasattr(item, 'raw_pred') else raw_output
                    except:
                        accumulated_raw = raw_output
                    
                    # Only extract if raw_pred contains <answer> tag
                    if self.begin_of_answer_token.lower() in accumulated_raw.lower():
                        answer = extract_r1_answer(accumulated_raw, self.begin_of_answer_token, self.end_of_answer_token)
                        
                        # DOUBLE CHECK: Reject meaningless words
                        if answer and answer.lower().strip() in ['and', 'or', 'the', 'a', 'an']:
                            answer = None
                            print(f"WARNING: Rejected meaningless answer '{answer}' for item {item.id}")
                    
                    if answer is not None:
                        item.pred = answer
                        item.finish_flag = True
                        item.finish_reason = "Finished"
                    else:
                        # Don't set meaningless words as answer
                        # Only set step_output as pred if it's meaningful (not just "and", "the", etc.)
                        candidate_answer = step_output.strip()
                        if is_valid_answer(candidate_answer) and len(candidate_answer) > 3:
                            item.pred = candidate_answer
                        else:
                            item.pred = 'No valid answer found'
                        item.finish_flag = True
                        item.finish_reason = 'Normal finish without answer pattern'
                
            # do retrieval and add retrieved docs to prompt
            if len(step_query_list) > 0:
                # Log query improvements if enabled
                if self.use_query_improver:
                    for sq_item in step_query_list[:3]:  # 只打印前3个作为示例
                        if 'original_query' in sq_item:
                            print(f"  Query improved: '{sq_item['original_query'][:50]}...' -> '{sq_item['query'][:50]}...'")
                
                query_list = [it['query'] for it in step_query_list]
                item_list = [it['item'] for it in step_query_list]
                retrieved_docs = self.retriever.batch_search(query_list)
                
                # 处理多查询策略：合并来自同一 item 的多个查询的结果
                item_to_results = {}
                for sq_item, query, docs in zip(step_query_list, query_list, retrieved_docs):
                    item = sq_item['item']
                    if item not in item_to_results:
                        item_to_results[item] = {
                            'queries': [],
                            'docs': [],
                            'doc_ids': set()  # 用于去重
                        }
                    
                    # 记录查询（包括原始和改进后的）
                    query_info = {'query': query}
                    if 'original_query' in sq_item:
                        query_info['original_query'] = sq_item['original_query']
                    item_to_results[item]['queries'].append(query_info)
                    
                    # 合并文档（去重）
                    for doc in docs:
                        doc_id = doc.get('id', '')
                        if doc_id and doc_id not in item_to_results[item]['doc_ids']:
                            item_to_results[item]['docs'].append(copy.copy(doc))
                            item_to_results[item]['doc_ids'].add(doc_id)
                
                # 存储检索结果并添加到 prompt
                for item, results in item_to_results.items():
                    # 使用第一个查询作为主查询（用于显示）
                    main_query = results['queries'][0]['query']
                    item.retrieval_results[str(item.retrieved_times)] = {
                        'query': main_query,
                        'queries': results['queries'] if len(results['queries']) > 1 else None,  # 如果有多个查询才保存
                        'docs': copy.copy(results['docs'])
                    }
                    # 添加检索到的文档到 prompt
                    format_doc_string = self._retrieved_docs_to_string(results['docs'])
                    item.prompt += format_doc_string
                    item.retrieved_times += 1

        dataset = self.evaluate(dataset, do_eval=do_eval, pred_process_fun=pred_process_fun)
        return dataset

def main():
    parser = argparse.ArgumentParser(description="Run SearchR1 Pipeline with Refiner.")
    parser.add_argument("--config", type=Path, default=Path("configs/r1_search_v1.yaml"))
    parser.add_argument("--split", default="test", help="Dataset split to evaluate.")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--sample-num", type=int, default=None)
    
    args = parser.parse_args()

    # Build Config
    overrides = {}
    if args.data_dir: overrides["data_dir"] = args.data_dir
    if args.output_dir: overrides["save_dir"] = args.output_dir
    if args.sample_num: overrides["test_sample_num"] = args.sample_num
    
    config = Config(config_file_path=str(args.config), config_dict=overrides)
    
    # Load Dataset
    dataset_splits = get_dataset(config)
    dataset = dataset_splits[args.split]
    
    if config['test_sample_num'] is not None:
        dataset_items = dataset[:config['test_sample_num']]
        dataset = Dataset(config=config, data=dataset_items)
    
    print(f"Loaded {len(dataset)} samples.")

    # Initialize Pipeline
    print("Initializing RefinedSearchR1Pipeline...")
    # Use custom concise prompt template
    prompt_template = ConciseSearchR1PromptTemplate(config)
    pipeline = RefinedSearchR1Pipeline(config, prompt_template=prompt_template)
    
    # Run
    print("Running pipeline...")
    result = pipeline.run(dataset, do_eval=True)
    
    print(f"Results saved to {config['save_dir']}")

if __name__ == "__main__":
    main()
