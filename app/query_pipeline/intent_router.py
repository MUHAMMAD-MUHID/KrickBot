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
    Stub for the future LLM-based router.
    To be implemented once LLM provider is chosen.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        
    def route(self, query: str) -> Intent:
        # TODO: Send query to LLM with a 0-shot prompt:
        # "Classify the following cricket question into FACTUAL, EXPLANATORY, or CHITCHAT: {query}"
        raise NotImplementedError("LLM router not yet implemented")

# Global instance of the active router
router = IntentRouter()

def route_query(query: str) -> Intent:
    """Convenience function to route a query."""
    return router.route(query)
