"""
Test script for the Intent Router.
Tests various user queries to ensure they are classified into the
correct buckets (FACTUAL, EXPLANATORY, CHITCHAT).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.query_pipeline.intent_router import route_query, Intent
from app.utils.logger import get_logger

logger = get_logger(__name__)

test_cases = [
    # CHITCHAT
    ("Hi", Intent.CHITCHAT),
    ("Hello bot", Intent.CHITCHAT),
    ("Who are you?", Intent.CHITCHAT),
    
    # FACTUAL (Text-to-SQL)
    ("How many runs did Babar score in the last match?", Intent.FACTUAL),
    ("Who took the most wickets in Haripur?", Intent.FACTUAL),
    ("What was the highest score?", Intent.FACTUAL),
    
    # EXPLANATORY (RAG)
    ("Explain the rules of a super over", Intent.EXPLANATORY),
    ("Tell me about the history of Haripur cricket", Intent.EXPLANATORY),
    ("Compare the batting style of Babar and Rizwan", Intent.EXPLANATORY),
    ("Why did Attock win the match?", Intent.EXPLANATORY),
    
    # Fallback / Edge cases
    ("Babar Azam", Intent.EXPLANATORY), # Short entity search -> RAG
]

def test_router():
    logger.info("=" * 60)
    logger.info("Testing Intent Router")
    logger.info("=" * 60)
    
    passed = 0
    for query, expected in test_cases:
        result = route_query(query)
        if result == expected:
            logger.info(f"[PASS] '{query}' -> {result}")
            passed += 1
        else:
            logger.error(f"[FAIL] '{query}' -> Got {result}, Expected {expected}")
            
    logger.info("-" * 60)
    logger.info(f"Results: {passed}/{len(test_cases)} passed.")
    if passed == len(test_cases):
        logger.info("All tests passed successfully!")
    else:
        logger.error("Some tests failed.")

if __name__ == "__main__":
    test_router()
