"""
针对DeepSearch复杂问题的优化Prompt模板
"""
from flashrag.prompt.base_prompt import PromptTemplate


class DeepSearchPromptTemplate(PromptTemplate):
    """
    针对复杂多跳推理问题的优化prompt模板
    """
    
    base_system_prompt = (
        "You are an expert at answering complex questions that require multi-step reasoning and information synthesis.\n"
        "Your task is to carefully analyze the provided documents and answer the question step by step.\n\n"
        "Instructions:\n"
        "1. Read all the provided documents carefully\n"
        "2. Identify relevant information from each document\n"
        "3. Connect information across documents if needed\n"
        "4. Reason step by step to arrive at the answer\n"
        "5. Provide a concise, direct answer based on the evidence\n\n"
        "The following documents are provided:\n\n{reference}"
    )
    
    base_user_prompt = (
        "Question: {question}\n\n"
        "Please analyze the documents and provide your answer. "
        "If the information is not sufficient, explain what is missing. "
        "Otherwise, provide a clear and concise answer."
    )
    
    def __init__(self, config, **kwargs):
        # 使用自定义的prompt模板
        super().__init__(
            config,
            system_prompt=self.base_system_prompt,
            user_prompt=self.base_user_prompt,
            **kwargs
        )

