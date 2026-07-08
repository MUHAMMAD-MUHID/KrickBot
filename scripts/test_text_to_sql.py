"""
Test script for the Text-to-SQL Engine.
Tests the Gemini prompt generation, SQL validation, and database execution.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.query_pipeline.text_to_sql import answer_factual_query
from app.utils.logger import get_logger

logger = get_logger(__name__)

def run_tests():
    logger.info("=" * 60)
    logger.info("Testing Text-to-SQL Engine")
    logger.info("=" * 60)
    
    test_queries = [
        "What is the highest score ever scored by a player in a single match?",
        "How many wickets were taken by player with ID 1?",
        "What is the format of the tournament named 'PSL'?"
    ]
    
    for query in test_queries:
        logger.info(f"\nUser Query: '{query}'")
        result = answer_factual_query(query)
        
        if result.get("error"):
            logger.error(f"Error: {result['error']}")
            if result.get("sql"):
                logger.error(f"Generated SQL: {result['sql']}")
        else:
            logger.info(f"Generated SQL: {result['sql']}")
            logger.info(f"Results: {json.dumps(result['results'], indent=2, default=str)}")

if __name__ == "__main__":
    run_tests()
