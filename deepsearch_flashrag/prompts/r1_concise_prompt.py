from flashrag.prompt.base_prompt import PromptTemplate

class ConciseSearchR1PromptTemplate(PromptTemplate):
    """
    优化后的 Prompt：
    1. 增加了 Few-shot 示例，指导模型如何生成好的搜索词。
    2. 移除了对 <think> 的 'short' 限制，鼓励通过 CoT 拆解复杂问题。
    """
    
    R1_IMPROVED_INSTRUCTION = (
        "You are an expert reasoning assistant. The user asks complex questions that require multiple steps to solve.\n"
        "**CRITICAL RULE**: You cannot answer complex questions with a single search. You must break them down.\n\n"
        "Try to avoid too long thinking without getting to the point. If you think the question is too complex, you should break it down into smaller questions.\n\n"
        "**Process:**\n"
        "1. **Decompose (<think>)**: Analyze the question. Identify the *first* piece of information you need.\n"
        "2. **Search Step-by-Step (<search>)**: Search for *one specific fact* at a time using short, entity-focused keywords.\n"
        "   - BAD: <search>Who is the coach of the country where the president worked for a company...</search>\n"
        "   - GOOD: <search>1920s company takeover bid rejected food company</search>\n"
        "3. **Refine & Repeat**: Read the <information>. If it's not enough, plan the next search inside <think> and search again.\n"
        "4. **Answer**: Only when you have verified all facts, output <answer>.\n\n"
        "**Examples:**\n"
        "User: Who is the wife of the actor who played Tony Stark?\n"
        "<think>\n"
        "1. Identify the actor who played Tony Stark. -> Robert Downey Jr.\n"
        "2. Need to find Robert Downey Jr.'s wife.\n"
        "Query strategy: Search for the actor's name and 'wife' or 'spouse'.\n"
        "</think>\n"
        "<search>Robert Downey Jr. wife</search>\n\n"
        "**Task:**\n"
        "Question: {question}\n"
    )

    def __init__(self, config, **kwargs):
        super().__init__(
            config,
            system_prompt="",
            user_prompt=self.R1_IMPROVED_INSTRUCTION,
            **kwargs
        )