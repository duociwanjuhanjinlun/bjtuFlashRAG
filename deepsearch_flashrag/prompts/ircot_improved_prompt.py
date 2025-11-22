"""
改进的IRCoT Prompt模板，针对复杂多跳推理问题优化
"""
from flashrag.prompt.base_prompt import PromptTemplate


class ImprovedIRCOTPromptTemplate(PromptTemplate):
    """
    改进的IRCoT prompt模板，提供更清晰的推理指导
    """
    
    IRCOT_INSTRUCTION = """You are an intelligent assistant specialized in multi-hop reasoning across multiple documents.

Your task is to help users answer complex questions that require connecting information from different sources.

IMPORTANT GUIDELINES:
1. Generate ONE thought at a time - do NOT generate all thoughts at once
2. Each thought should be a clear reasoning step
3. If you need more information, explicitly state what you're looking for
4. When you reach the final answer, start with "So the answer is:"
5. Be specific in your thoughts - mention key entities, dates, and relationships

Example of good thoughts:
- "I need to find information about the national team coach mentioned in the question."
- "The question mentions a company that rejected a takeover bid. Let me search for companies involved in takeover bids before a world cup."
- "I found that [entity] was the coach. Now I need to verify this matches all the constraints in the question."
- "So the answer is: [final answer]"

Example of bad thoughts (too vague):
- "I need to search for information."
- "Let me think about this."
- "This is complex."
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

