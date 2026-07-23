"""
KrickBot — FastAPI Application Entry Point.

This is the main application file. It:
1. Creates the FastAPI app instance
2. Runs a startup check to verify MariaDB connectivity
3. Exposes a /health endpoint for monitoring
4. Will later expose /chat and /sync endpoints as we build more tasks

Start the server with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import get_db, check_db_connection
from app.update_pipeline.watermark import get_all_watermarks
from app.utils.logger import get_logger

logger = get_logger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once when the server starts.
    Verifies that MariaDB is reachable. Logs a clear error if not.
    """
    logger.info("KrickBot starting up...")
    if check_db_connection():
        logger.info("[OK] MariaDB connection OK.")
    else:
        logger.error(
            "[FAIL] Cannot connect to MariaDB. Check .env settings and ensure "
            "MariaDB is running on the configured host/port."
        )
    yield

# --- App Instance ---
app = FastAPI(
    title="KrickBot",
    description="AI-Powered Cricket Analytics Chatbot API",
    version="0.1.0",
    lifespan=lifespan,
)


# --- Health Check ---
@app.get("/health", tags=["System"])
def health_check():
    """
    Health check endpoint.

    Returns the application status and database connectivity.
    Use this for monitoring, load balancer checks, etc.
    """
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": "0.1.0",
    }


@app.get("/sync/status", tags=["Update Pipeline"])
def sync_status(db: Session = Depends(get_db)):
    """
    Show the current watermark state for all tracked tables.

    Useful for monitoring: see which tables have been synced,
    when they were last synced, and their current status.
    """
    watermarks = get_all_watermarks(db)
    return {
        "watermarks": [
            {
                "table_name": w.table_name,
                "last_synced_id": w.last_synced_id,
                "last_synced_at": w.last_synced_at.isoformat() if w.last_synced_at else None,
                "sync_status": w.sync_status,
                "updated_at": w.updated_at.isoformat() if w.updated_at else None,
            }
            for w in watermarks
        ]
    }

# --- Query Pipeline ---

from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from app.query_pipeline.intent_router import route_query, Intent
from app.query_pipeline.text_to_sql import answer_factual_query
from app.query_pipeline.response_generator import generate_response

# Add CORS middleware to allow the frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class RouteResponse(BaseModel):
    intent: Intent

class ChatResponse(BaseModel):
    response: str
    intent: Intent
    context: str | None = None

@app.post("/query/route", response_model=RouteResponse, tags=["Query Pipeline"])
def test_intent_router(request: QueryRequest):
    """
    Test endpoint for the Intent Router.
    Takes a query string and returns the classified Intent (FACTUAL, EXPLANATORY, CHITCHAT).
    """
    intent = route_query(request.query)
    return RouteResponse(intent=intent)

@app.post("/chat", response_model=ChatResponse, tags=["Query Pipeline"])
def chat_endpoint(request: QueryRequest):
    """
    Main Chat API. Takes user query, routes it, fetches context, and returns a natural language response.
    """
    query = request.query
    intent = route_query(query)
    context_str = ""
    
    if intent == Intent.FACTUAL:
        # Generate SQL and execute against DB
        sql_result = answer_factual_query(query)
        if sql_result.get("error"):
            context_str = f"Error retrieving data: {sql_result['error']}"
        else:
            context_str = f"Database Results:\n{sql_result.get('results', [])}"
            
    elif intent == Intent.EXPLANATORY:
        # TODO: RAG Retriever implementation (Task 7)
        context_str = "RAG retrieval is not yet implemented. Please answer generically based on cricket knowledge."
        
    elif intent == Intent.CHITCHAT:
        context_str = "This is a casual conversation. Be polite and helpful."
        
    # Generate final response
    final_answer = generate_response(query=query, context=context_str, intent=intent.value)
    
    return ChatResponse(
        response=final_answer,
        intent=intent,
        context=context_str if intent != Intent.CHITCHAT else None
    )
