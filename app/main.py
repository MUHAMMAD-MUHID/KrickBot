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

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, get_chat_db, check_db_connection
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
        try:
            from app.database import ChatBase, chat_engine
            import app.models.chat  # register models
            ChatBase.metadata.create_all(bind=chat_engine)
            logger.info("[OK] Chat history tables initialized.")
        except Exception as e:
            logger.warning(f"Chat table creation warning: {e}")
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
from app.query_pipeline.rag_retriever import retrieve_context
from app.query_pipeline.response_generator import generate_response
from app.query_pipeline.context_formatter import (
    format_factual_context,
    format_explanatory_context,
    format_chitchat_context,
)

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
    session_id: str | None = None

class RouteResponse(BaseModel):
    intent: Intent

class ChatResponse(BaseModel):
    response: str
    intent: Intent
    session_id: str
    context: str | None = None

class ChatMessageResponse(BaseModel):
    id: str | None = None
    role: str
    content: str
    intent: str | None
    created_at: str

class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageResponse]

class ChatSessionPreview(BaseModel):
    id: str
    preview: str
    updated_at: str

from app.models.chat import ChatSession, ChatMessage

@app.post("/query/route", response_model=RouteResponse, tags=["Query Pipeline"])
def test_intent_router(request: QueryRequest):
    """
    Test endpoint for the Intent Router.
    Takes a query string and returns the classified Intent (FACTUAL, EXPLANATORY, CHITCHAT).
    """
    intent = route_query(request.query)
    return RouteResponse(intent=intent)

@app.post("/chat", response_model=ChatResponse, tags=["Query Pipeline"])
def chat_endpoint(request: QueryRequest, chat_db: Session = Depends(get_chat_db)):
    """
    Main Chat API.

    Routes the user query, fetches data via the appropriate pipeline,
    formats it through context_formatter (stripping all SQL/implementation
    details), generates a KrickBot-style analyst response, and saves the
    interaction to the PostgreSQL chat history.
    """
    query = request.query
    session_id = request.session_id

    # Session management
    chat_session = None
    if session_id:
        chat_session = chat_db.query(ChatSession).filter(ChatSession.id == session_id).first()
    
    if not chat_session:
        chat_session = ChatSession()
        chat_db.add(chat_session)
        chat_db.commit()
        chat_db.refresh(chat_session)
    
    session_id = chat_session.id

    # Save user message and update session timestamp
    user_msg = ChatMessage(session_id=session_id, role="user", content=query)
    chat_db.add(user_msg)
    if chat_session:
        from datetime import datetime, timezone
        chat_session.updated_at = datetime.now(timezone.utc)
    chat_db.commit()

    intent = route_query(query)
    llm_context = ""       # Clean context sent to the LLM (no SQL leakage)
    debug_context = None   # Raw context returned in API response for debugging

    if intent == Intent.FACTUAL:
        # Generate SQL, execute, and format results for the LLM
        sql_result = answer_factual_query(query)
        llm_context = format_factual_context(sql_result, user_query=query)

        # Keep raw SQL in debug context (API response only, never sent to LLM)
        debug_context = f"SQL: {sql_result.get('sql', 'N/A')} | Rows: {len(sql_result.get('results', []))}"

    elif intent == Intent.EXPLANATORY:
        retrieved_docs = retrieve_context(query, top_k=3)
        if retrieved_docs:
            llm_context = format_explanatory_context(retrieved_docs)
            debug_context = f"RAG retrieval: found relevant context ({len(retrieved_docs)} chars)"
        else:
            llm_context = format_explanatory_context(
                "The knowledge base does not have detailed background information "
                "for this topic yet. You may suggest the user ask a specific stats question instead."
            )
            debug_context = "RAG retrieval: no documents found in vector_store"

    elif intent == Intent.CHITCHAT:
        llm_context = format_chitchat_context()

    # Generate final response — the LLM only sees clean, formatted context
    final_answer = generate_response(
        query=query,
        context=llm_context,
        intent=intent.value
    )

    # Save bot message
    bot_msg = ChatMessage(session_id=session_id, role="bot", content=final_answer, intent=intent.value)
    chat_db.add(bot_msg)
    chat_db.commit()

    return ChatResponse(
        response=final_answer,
        intent=intent,
        session_id=session_id,
        context=debug_context
    )

@app.get("/chat/{session_id}", response_model=ChatHistoryResponse, tags=["Query Pipeline"])
def get_chat_history(session_id: str, chat_db: Session = Depends(get_chat_db)):
    """
    Retrieve the full chat history for a given session.
    """
    chat_session = chat_db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    messages = []
    for msg in chat_session.messages:
        messages.append(ChatMessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            intent=msg.intent,
            created_at=msg.created_at.isoformat() if msg.created_at else ""
        ))
    
    return ChatHistoryResponse(
        session_id=session_id,
        messages=messages
    )

@app.get("/chats", response_model=list[ChatSessionPreview], tags=["Query Pipeline"])
def get_all_chats(chat_db: Session = Depends(get_chat_db)):
    """
    Retrieve all chat sessions ordered by most recently updated.
    """
    sessions = chat_db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
    
    previews = []
    for session in sessions:
        # Find the first user message for the preview
        preview_text = "New Chat"
        first_msg = next((m for m in session.messages if m.role == "user"), None)
        if first_msg:
            preview_text = first_msg.content[:50] + ("..." if len(first_msg.content) > 50 else "")
            
        previews.append(ChatSessionPreview(
            id=session.id,
            preview=preview_text,
            updated_at=session.updated_at.isoformat() if session.updated_at else ""
        ))
        
    return previews

@app.delete("/chat/{session_id}/truncate/{message_id}", tags=["Query Pipeline"])
def truncate_chat(session_id: str, message_id: str, chat_db: Session = Depends(get_chat_db)):
    """
    Truncate the chat session by deleting all messages that occur AFTER the given message_id.
    Also deletes the specified message itself (so the user can resubmit it).
    """
    # Find the target message
    target_msg = chat_db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.id == message_id
    ).first()

    if not target_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    # Delete all messages created at or after the target message
    chat_db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.created_at >= target_msg.created_at
    ).delete(synchronize_session=False)

    chat_db.commit()
    
    return {"status": "success", "deleted_from": target_msg.created_at.isoformat()}
