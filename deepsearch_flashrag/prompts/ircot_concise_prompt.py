"""
针对DeepSearch优化的IRCoT Prompt模板
强调生成简洁、精炼的最终答案
"""
from flashrag.prompt.base_prompt import PromptTemplate


class ConciseIRCOTPromptTemplate(PromptTemplate):
    """
    优化的IRCoT prompt模板，强调简洁答案
    """
    
    IRCOT_INSTRUCTION = """You are an intelligent assistant specialized in multi-hop reasoning across multiple documents.

Your task is to help users answer complex questions that require connecting information from different sources.

CRITICAL GUIDELINES:
1. Generate ONE thought at a time - do NOT generate all thoughts at once
2. Each thought should be a clear, concise reasoning step
3. Be specific - mention key entities, dates, and relationships
4. When you reach the final answer, you MUST start with "So the answer is:" (for English) or "答案是：" (for Chinese) followed by ONLY the answer
5. The final answer should be SHORT and PRECISE - just the answer itself, no explanation
6. The answer format should match the language of the question (English questions → English answers, Chinese questions → Chinese answers)

Example of good thoughts (English):
- "I need to find information about the national team coach mentioned in the question."
- "The question mentions a company that rejected a takeover bid. Let me search for companies involved in takeover bids before a world cup."
- "I found that [entity] was the coach. Now I need to verify this matches all the constraints in the question."
- "So the answer is: [final answer]"  ← This is the format for final answer

Example of good thoughts (Chinese):
- "我需要找到问题中提到的国家队教练的信息。"
- "问题提到了一家公司拒绝了收购要约。让我搜索世界杯前涉及收购的公司。"
- "我找到了[实体]是教练。现在我需要验证这是否符合问题的所有约束条件。"
- "答案是：[最终答案]"  ← 这是最终答案的格式

Example of bad thoughts (too verbose):
- "To solve this complex question, let's break it down step-by-step: 1. We need to identify..."
- "Let me think about this carefully and analyze all the information..."
- Long explanations without getting to the point

REMEMBER: 
- For English questions, write "So the answer is: [answer]" - nothing more, nothing less.
- For Chinese questions, write "答案是：[答案]" - 不要多余的内容。
"""
    
    IRCOT_EXAMPLE = """Wikipedia Title: Kurram Garhi
Kurram Garhi is a small village located near the city of Bannu, which is the part of Khyber Pakhtunkhwa province of Pakistan. Its population is approximately 35000. Barren hills are near this village. This village is on the border of Kurram Agency. Other nearby villages are Peppal, Surwangi and Amandi Kala.

Wikipedia Title: 2001–02 UEFA Champions League second group stage
Eight winners and eight runners- up from the first group stage were drawn into four groups of four teams, each containing two group winners and two runners- up. Teams from the same country or from the same first round group could not be drawn together. The top two teams in each group advanced to the quarter- finals.

Wikipedia Title: Satellite tournament
A satellite tournament is either a minor tournament or event on a competitive sporting tour or one of a group of such tournaments that form a series played in the same country or region.

Wikipedia Title: Trojkrsti
Trojkrsti is a village in Municipality of Prilep, Republic of Macedonia.

Wikipedia Title: Telephone numbers in Ascension Island
Country Code:+ 247< br> International Call Prefix: 00 Ascension Island does not share the same country code( +290) with the rest of St Helena.

Question: Are both Kurram Garhi and Trojkrsti located in the same country?
Thought: Kurram Garhi is located in the country of Pakistan. Trojkrsti is located in the country of Republic of Macedonia. Thus, they are not in the same country. So the answer is: no.
"""
    
    def __init__(self, config, **kwargs):
        # 使用改进的instruction和example
        system_prompt = f"{self.IRCOT_INSTRUCTION}\n\n{self.IRCOT_EXAMPLE}"
        user_prompt = "{reference}Question: {question}\nThought:"
        reference_template = "Wikipedia Title: {title}\n{text}\n\n"
        
        super().__init__(
            config,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            reference_template=reference_template,
            **kwargs
        )

