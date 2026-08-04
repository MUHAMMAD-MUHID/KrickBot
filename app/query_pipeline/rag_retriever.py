"""
RAG Retriever — Hybrid Vector + Keyword Search for Explanatory/Comparative Questions.

Searches MariaDB's vector_store table using:
1. Dense Vector Search (VEC_DISTANCE_COSINE with BAAI/bge-small-en-v1.5)
2. Sparse Keyword Search (FULLTEXT MATCH AGAINST)
3. Reciprocal Rank Fusion (RRF) to merge candidate lists
"""

from typing import List, Dict, Any
from sqlalchemy import text
from app.database import engine
from app.update_pipeline.embedder import get_model
from app.utils.logger import get_logger

logger = get_logger(__name__)


def retrieve_context(query: str, top_k: int = 3) -> str:
    """
    Retrieves relevant knowledge base documents for an explanatory query.

    Args:
        query: User question string
        top_k: Number of top documents to return

    Returns:
        A combined string of retrieved document contents for LLM synthesis
    """
    if not query or not query.strip():
        return ""

    try:
        # 1. Embed user query using local model
        model = get_model()
        query_emb = model.encode(query)
        emb_str = "[" + ",".join(str(f) for f in query_emb) + "]"

        vector_docs: List[Dict[str, Any]] = []
        keyword_docs: List[Dict[str, Any]] = []

        with engine.begin() as conn:
            # 2a. Dense Vector Search
            try:
                vec_sql = text("""
                    SELECT doc_id, content, metadata, VEC_DISTANCE_COSINE(embedding, VEC_FromText(:emb)) AS distance
                    FROM vector_store
                    ORDER BY distance ASC
                    LIMIT 10
                """)
                vec_rows = conn.execute(vec_sql, {"emb": emb_str}).fetchall()
                vector_docs = [{"doc_id": r.doc_id, "content": r.content} for r in vec_rows]
            except Exception as ve:
                logger.warning(f"Vector search warning: {ve}")

            # 2b. Sparse Keyword Search (Fulltext)
            try:
                kw_sql = text("""
                    SELECT doc_id, content, MATCH(content) AGAINST(:query IN NATURAL LANGUAGE MODE) AS rel
                    FROM vector_store
                    WHERE MATCH(content) AGAINST(:query IN NATURAL LANGUAGE MODE) > 0
                    ORDER BY rel DESC
                    LIMIT 10
                """)
                kw_rows = conn.execute(kw_sql, {"query": query}).fetchall()
                keyword_docs = [{"doc_id": r.doc_id, "content": r.content} for r in kw_rows]
            except Exception as kwe:
                logger.warning(f"Keyword search warning: {kwe}")

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        doc_contents: Dict[str, str] = {}

        for rank, doc in enumerate(vector_docs):
            doc_id = doc["doc_id"]
            doc_contents[doc_id] = doc["content"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (60.0 + rank + 1))

        for rank, doc in enumerate(keyword_docs):
            doc_id = doc["doc_id"]
            doc_contents[doc_id] = doc["content"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (60.0 + rank + 1))

        if not rrf_scores:
            logger.info("No RAG documents retrieved from vector_store.")
            return ""

        # 4. Sort by RRF score and take top_k
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)[:top_k]
        top_contents = [doc_contents[did] for did in sorted_doc_ids]

        context = "\n\n".join(top_contents)
        logger.info(f"RAG Retriever found {len(top_contents)} relevant documents.")
        return context

    except Exception as e:
        logger.error(f"Error in RAG retrieval: {e}")
        return ""
