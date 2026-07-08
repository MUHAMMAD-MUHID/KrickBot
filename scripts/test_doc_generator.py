"""
Test script for Task 2: Document Generator

Runs delta extractor for a few tables and passes the results to the document generator
to visually inspect the natural language text and deterministic IDs.
"""

import sys
import os

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.update_pipeline.delta_extractor import extract_delta_rows
from app.update_pipeline.document_generator import generate_documents_from_rows
from app.utils.logger import get_logger

logger = get_logger(__name__)

def test_generation():
    logger.info("Starting Document Generator Test...")
    db = SessionLocal()
    try:
        # Test 1: Player Table
        logger.info("\n--- Testing Player Documents ---")
        player_rows = extract_delta_rows(db, "player", last_id=0, batch_size=3)
        player_docs = generate_documents_from_rows("player", player_rows)
        for doc in player_docs:
            print(f"ID: {doc.doc_id}")
            print(f"Text: {doc.content}")
            print("-" * 40)

        # Test 2: Matches Table
        logger.info("\n--- Testing Match Documents ---")
        match_rows = extract_delta_rows(db, "matches", last_id=0, batch_size=2)
        match_docs = generate_documents_from_rows("matches", match_rows)
        for doc in match_docs:
            print(f"ID: {doc.doc_id}")
            print(f"Text: {doc.content}")
            print("-" * 40)
            
        # Test 3: Batting Detail
        logger.info("\n--- Testing Batting Performance Documents ---")
        batting_rows = extract_delta_rows(db, "batting_detail", last_id=0, batch_size=3)
        batting_docs = generate_documents_from_rows("batting_detail", batting_rows)
        for doc in batting_docs:
            print(f"ID: {doc.doc_id}")
            print(f"Text: {doc.content}")
            print("-" * 40)
            
        # Test 4: Bowling Detail
        logger.info("\n--- Testing Bowling Performance Documents ---")
        bowling_rows = extract_delta_rows(db, "bowling_detail", last_id=0, batch_size=3)
        bowling_docs = generate_documents_from_rows("bowling_detail", bowling_rows)
        for doc in bowling_docs:
            print(f"ID: {doc.doc_id}")
            print(f"Text: {doc.content}")
            print("-" * 40)

    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_generation()
