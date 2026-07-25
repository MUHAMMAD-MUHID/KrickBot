"""
Script to create PostgreSQL tables for chat history.
Run this script once to initialize the chat database schema.
"""

import sys
import os

# Add the project root to the python path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import chat_engine, ChatBase
from app.models.chat import ChatSession, ChatMessage
from app.utils.logger import get_logger

logger = get_logger(__name__)

def init_db():
    logger.info("Creating chat tables in PostgreSQL...")
    try:
        ChatBase.metadata.create_all(bind=chat_engine)
        logger.info("Successfully created chat tables.")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
