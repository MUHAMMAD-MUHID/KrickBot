"""
Intent Router module.

Classifies incoming user queries into one of three buckets:
- FACTUAL: Requires exact numbers/stats (routes to Text-to-SQL)
- EXPLANATORY: Requires context/narrative (routes to RAG)
- CHITCHAT: General conversation (routes to simple generation)
"""

from enum import Enum
import re
from app.utils.logger import get_logger

logger = get_logger(__name__)

class Intent(str, Enum):
    FACTUAL = "FACTUAL"
    EXPLANATORY = "EXPLANATORY"
    CHITCHAT = "CHITCHAT"

class IntentRouter:
    """
    Routes a user query to the appropriate intent using a fast rule-based classifier.
    """
    
    def __init__(self):
        # Keywords indicating a factual, numeric, or statistical query
        self.factual_keywords = [
            "how many", "how much", "who scored", "who took", "most", "highest", 
            "lowest", "average", "strike rate", "wickets", "runs", "stats", 
            "score", "won", "lost", "centuries", "fifties", "date", "when", 
            "compare", "vs", "versus", "better than"
        ]
        
        # Keywords indicating an explanatory or narrative query
        self.explanatory_keywords = [
            "why", "explain", "difference", "rules", "history", 
            "tell me about", "what happened", "describe", "meaning"
        ]
        
        # Keywords indicating chitchat
        self.chitchat_keywords = [
            "hi", "hello", "hey", "who are you", "what can you do", "thanks", "bye"
        ]

    def route(self, query: str) -> Intent:
        """
        Classifies the query.
        Returns the Intent Enum.
        """
        lower_query = query.lower()
        
        # 1. Check for Chitchat
        if len(lower_query.split()) <= 4:
            for kw in self.chitchat_keywords:
                if re.search(rf'\b{kw}\b', lower_query) and lower_query.startswith(kw):
                    logger.debug(f"Router classified as CHITCHAT: '{query}'")
                    return Intent.CHITCHAT
                    
        # 2. Check for Factual first (so 'compare' hits before explanatory keywords)
        for kw in self.factual_keywords:
            if re.search(rf'\b{kw}\b', lower_query):
                logger.debug(f"Router classified as FACTUAL: '{query}'")
                return Intent.FACTUAL
                
        # 3. Check for Explanatory
        for kw in self.explanatory_keywords:
            if re.search(rf'\b{kw}\b', lower_query):
                logger.debug(f"Router classified as EXPLANATORY: '{query}'")
                return Intent.EXPLANATORY
                
        # Fallback: if it's a short query, default to FACTUAL (e.g. "Babar Azam stats")
        if len(lower_query.split()) <= 3:
            logger.debug(f"Router classified as FACTUAL (fallback short): '{query}'")
            return Intent.FACTUAL
            
        # Default Fallback
        logger.debug(f"Router classified as EXPLANATORY (default fallback): '{query}'")
        return Intent.EXPLANATORY


class LLMIntentRouter:
    """
    LLM-based router using Groq API to classify incoming queries with few-shot examples.
    """
    def __init__(self, api_key: str = None):
        from groq import Groq
        from app.config import settings
        self.api_key = api_key or settings.GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        
    def route(self, query: str) -> Intent:
        if not self.client:
            logger.warning(f"Groq API key missing. Falling back to rule-based router for query: '{query}'")
            return IntentRouter().route(query)
            
        system_prompt = (
            "You are an intent classification system for a cricket chatbot. "
            "Classify the user query into exactly one of these three categories:\n"
            "1. FACTUAL: Queries asking for exact numbers, stats, scores, dates, database lookups, or statistical comparisons between players/teams.\n"
            "2. EXPLANATORY: Queries asking for context, narratives, non-statistical rules, 'who is', or 'why/how' questions.\n"
            "3. CHITCHAT: Greetings or general conversation ONLY.\n\n"
            "Examples:\n"
            "- Query: 'Compare Babar Azam and Shoaib Malik'\n  Output: {\"intent\": \"FACTUAL\"}\n"
            "- Query: 'What is the highest score by Kohli'\n  Output: {\"intent\": \"FACTUAL\"}\n"
            "- Query: 'Explain the rules of a super over'\n  Output: {\"intent\": \"EXPLANATORY\"}\n"
            "- Query: 'Who is better, Shaheen or Haris Rauf'\n  Output: {\"intent\": \"FACTUAL\"}\n"
            "- Query: 'Tell me about the history of the Ashes'\n  Output: {\"intent\": \"EXPLANATORY\"}\n"
            "- Query: 'Hello krickbot'\n  Output: {\"intent\": \"CHITCHAT\"}\n\n"
            "Respond ONLY with a JSON object in this exact format: {\"intent\": \"CATEGORY\"}"
        )
        
        try:
            import json
            completion = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}"}
                ],
                temperature=0.0,
                max_tokens=20,
                response_format={"type": "json_object"}
            )
            result_str = completion.choices[0].message.content.strip()
            
            try:
                data = json.loads(result_str)
                intent_val = data.get("intent", "").upper()
            except Exception:
                intent_val = result_str.upper()
            
            if "FACTUAL" in intent_val:
                return Intent.FACTUAL
            elif "EXPLANATORY" in intent_val:
                return Intent.EXPLANATORY
            elif "CHITCHAT" in intent_val:
                return Intent.CHITCHAT
            else:
                logger.warning(f"Unexpected LLM output '{result_str}'. Defaulting to FACTUAL.")
                return Intent.FACTUAL
        except Exception as e:
            logger.warning(f"Groq routing error: {str(e)}. Falling back to rule-based router for query: '{query}'")
            return IntentRouter().route(query)

# Global instance of the active router
# Switch to LLMIntentRouter now that Groq is available
router = LLMIntentRouter()

def route_query(query: str) -> Intent:
    """Convenience function to route a query."""
    return router.route(query)
