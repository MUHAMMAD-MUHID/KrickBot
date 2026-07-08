"""
Embedder — embeds documents and upserts them into the vector store.

This module initializes the local BAAI/bge-small-en-v1.5 model,
generates 384-dimensional embeddings, and inserts them into MariaDB
using native VECTOR types.
"""

from typing import List
import json
from sqlalchemy import text
from sentence_transformers import SentenceTransformer
from app.database import engine
from app.update_pipeline.document_generator import Document
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize model lazily to avoid loading it on fast API startup
_model = None

def get_model():
    global _model
    if _model is None:
        logger.info("Loading BAAI/bge-small-en-v1.5 embedding model...")
        _model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    return _model

def embed_and_upsert(documents: List[Document]) -> bool:
    """
    Calculates embeddings for the provided documents and upserts
    them into MariaDB's vector_store table.
    Returns True if successful, False otherwise.
    """
    if not documents:
        return True
        
    try:
        model = get_model()
        
        # 1. Calculate embeddings
        texts = [doc.content for doc in documents]
        logger.info(f"Calculating embeddings for {len(documents)} documents...")
        embeddings = model.encode(texts)
        
        # 2. Upsert to MariaDB
        with engine.begin() as conn:
            query = text("""
                INSERT INTO vector_store (doc_id, content, metadata, embedding)
                VALUES (:doc_id, :content, :metadata, VEC_FromText(:embedding))
                ON DUPLICATE KEY UPDATE 
                    content = VALUES(content),
                    metadata = VALUES(metadata),
                    embedding = VALUES(embedding)
            """)
            
            params = []
            for doc, emb in zip(documents, embeddings):
                # MariaDB expects a string representation of the array for VEC_FromText
                emb_str = "[" + ",".join(str(f) for f in emb) + "]"
                params.append({
                    "doc_id": doc.doc_id,
                    "content": doc.content,
                    "metadata": json.dumps(doc.metadata) if doc.metadata else "{}",
                    "embedding": emb_str
                })
                
            logger.info(f"Upserting {len(params)} documents into vector_store...")
            conn.execute(query, params)
            
        return True
        
    except Exception as e:
        logger.error(f"Failed to embed and upsert documents: {e}")
        return False
