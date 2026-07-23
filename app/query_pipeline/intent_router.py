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
    Routes a user query to the appropriate intent.
    Currently uses a fast rule-based classifier as a placeholder until
    the LLM provider (Gemini/Local Llama) is finalized in Task 8.
    """
    
    def __init__(self):
        # Keywords indicating a factual, numeric, or statistical query
        self.factual_keywords = [
            "how many", "how much", "who scored", "who took", "most", "highest", 
            "lowest", "average", "strike rate", "wickets", "runs", "stats", 
            "score", "won", "lost", "centuries", "fifties", "date", "when"
        ]
        
        # Keywords indicating an explanatory or narrative query
        self.explanatory_keywords = [
            "why", "explain", "compare", "difference", "rules", "history", 
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
        # If the query is very short and matches chitchat exactly or starts with it
        if len(lower_query.split()) <= 4:
            for kw in self.chitchat_keywords:
                if lower_query.startswith(kw) or lower_query == kw:
                    logger.debug(f"Router classified as CHITCHAT: '{query}'")
                    return Intent.CHITCHAT
                    
        # 2. Check for Explanatory
        for kw in self.explanatory_keywords:
            if kw in lower_query:
                logger.debug(f"Router classified as EXPLANATORY: '{query}'")
                return Intent.EXPLANATORY
                
        # 3. Check for Factual
        for kw in self.factual_keywords:
            if kw in lower_query:
                logger.debug(f"Router classified as FACTUAL: '{query}'")
                return Intent.FACTUAL
                
        # Fallback: if it's a very short query without keywords, assume it's a name search (RAG)
        if len(lower_query.split()) <= 3:
            logger.debug(f"Router classified as EXPLANATORY (fallback short): '{query}'")
            return Intent.EXPLANATORY
            
        # Default Fallback
        logger.debug(f"Router classified as FACTUAL (default fallback): '{query}'")
        return Intent.FACTUAL


class LLMIntentRouter:
    """
    LLM-based router using Groq API to classify incoming queries.
    """
    def __init__(self, api_key: str = None):
        from groq import Groq
        from app.config import settings
        self.api_key = api_key or settings.GROQ_API_KEY
        self.client = Groq(api_key=self.api_key) if self.api_key else None
        
    def route(self, query: str) -> Intent:
        if not self.client:
            logger.warning("Groq API key missing. Falling back to rule-based router.")
            return IntentRouter().route(query)
            
        system_prompt = (
            "You are an intent classification system for a cricket chatbot. "
            "Classify the following query into exactly one of these three categories:\n"
            "1. FACTUAL: Queries asking for exact numbers, stats, scores, dates, or database lookups.\n"
            "2. EXPLANATORY: Queries asking for context, narratives, comparisons, rules, 'who is', or 'why/how' questions.\n"
            "3. CHITCHAT: Greetings or general conversation ONLY. If the query contains a greeting PLUS a substantive question (e.g., 'hello who is...'), classify it as EXPLANATORY or FACTUAL based on the question.\n"
            "Respond ONLY with the category name (FACTUAL, EXPLANATORY, or CHITCHAT) and nothing else."
        )
        
        try:
            completion = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {query}"}
                ],
                temperature=0.0,
                max_tokens=10,
            )
            result = completion.choices[0].message.content.strip().upper()
            
            if "FACTUAL" in result:
                return Intent.FACTUAL
            elif "EXPLANATORY" in result:
                return Intent.EXPLANATORY
            elif "CHITCHAT" in result:
                return Intent.CHITCHAT
            else:
                logger.warning(f"Unexpected LLM output '{result}'. Defaulting to FACTUAL.")
                return Intent.FACTUAL
        except Exception as e:
            logger.error(f"Groq routing error: {str(e)}. Falling back to rule-based router.")
            return IntentRouter().route(query)

# Global instance of the active router
# Switch to LLMIntentRouter now that Groq is available
router = LLMIntentRouter()

def route_query(query: str) -> Intent:
    """Convenience function to route a query."""
    return router.route(query)
