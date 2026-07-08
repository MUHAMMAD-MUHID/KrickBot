"""
Database connection module for KrickBot.

Creates a SQLAlchemy engine and session factory connected to MariaDB.
All database access in the application goes through this module.

Design decisions:
- Synchronous engine (not async) because our workload is batch-heavy (update pipeline)
  and the query pipeline's DB calls are simple and fast. Async adds complexity without
  meaningful benefit here.
- Connection pool with sensible defaults for a single-server deployment.
- Session factory via sessionmaker for use in FastAPI dependency injection.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# --- Engine ---
# pool_size=5: keep 5 connections ready (enough for API + update pipeline)
# max_overflow=10: allow up to 10 extra connections under burst load
# pool_recycle=3600: recycle connections every hour to avoid MariaDB's wait_timeout
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    echo=False,  # Set to True to log all SQL (very verbose, use for debugging only)
)

# --- Session Factory ---
# autocommit=False: we explicitly commit transactions
# autoflush=False: we control when SQLAlchemy flushes to DB (avoids surprise queries)
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# --- Declarative Base ---
# All ORM models inherit from this base class
Base = declarative_base()


def get_db() -> Session:
    """
    FastAPI dependency that provides a database session.

    Usage in a route:
        @app.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    The session is automatically closed after the request completes,
    even if an exception occurs (finally block).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Test that we can actually connect to MariaDB and run a query.
    Returns True if successful, False otherwise.
    Used by the /health endpoint and startup checks.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified successfully.")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
