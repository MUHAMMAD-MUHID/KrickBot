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

# --- App Instance ---
app = FastAPI(
    title="KrickBot",
    description="AI-Powered Cricket Analytics Chatbot API",
    version="0.1.0",
)


# --- Startup Event ---
@app.on_event("startup")
def on_startup():
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


# --- Watermark Status ---
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
