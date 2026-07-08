"""
Test script for the Vector Database.
Embeds a single dummy document, saves it to MariaDB,
and then retrieves it to verify the vector stored correctly.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine
from app.update_pipeline.document_generator import Document
from app.update_pipeline.embedder import embed_and_upsert
from app.utils.logger import get_logger

logger = get_logger(__name__)

def test_vector_store():
    logger.info("Creating a test document...")
    doc = Document(
        doc_id="test::1",
        content="This is a test document about cricket for vector database validation.",
        metadata={"type": "test"}
    )
    
    logger.info("Upserting into vector_store...")
    success = embed_and_upsert([doc])
    
    if not success:
        logger.error("Failed to upsert test document.")
        return
        
    logger.info("Upsert successful. Now querying it back to verify...")
    
    with engine.connect() as conn:
        # VEC_ToText converts the vector back into a readable JSON array string
        result = conn.execute(text("""
            SELECT doc_id, content, metadata, VEC_ToText(embedding) as emb_str
            FROM vector_store
            WHERE doc_id = 'test::1'
        """)).fetchone()
        
        if result:
            logger.info("Found document in vector_store!")
            logger.info(f"ID: {result[0]}")
            logger.info(f"Content: {result[1]}")
            logger.info(f"Metadata: {result[2]}")
            
            # Print first 5 dimensions of the 384-d vector
            emb_str = result[3]
            try:
                # emb_str is '[0.1, 0.2, ...]'
                floats = eval(emb_str)
                logger.info(f"Vector dimension: {len(floats)}")
                logger.info(f"First 5 values: {floats[:5]}")
            except Exception as e:
                logger.error(f"Failed to parse vector: {e}")
        else:
            logger.error("Document not found in vector_store.")

if __name__ == "__main__":
    test_vector_store()
