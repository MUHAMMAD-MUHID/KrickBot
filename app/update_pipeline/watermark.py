"""
Watermark operations for the update pipeline.

Provides functions to read, advance, and manage sync watermarks.
These are the core primitives that the delta extractor and update pipeline
will use to track progress.

Critical invariant:
  advance_watermark() must ONLY be called after a successful write to the
  vector store. Never before. This ensures idempotent retries.
"""

from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from app.models.sync_state import SyncState
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_watermark(db: Session, table_name: str) -> Tuple[int, Optional[datetime]]:
    """
    Read the current watermark for a given table.

    Args:
        db: Active database session.
        table_name: Name of the source table (e.g., 'matches').

    Returns:
        Tuple of (last_synced_id, last_synced_at).
        Returns (0, None) if the table has no watermark entry yet.
    """
    record = db.query(SyncState).filter(SyncState.table_name == table_name).first()
    if record is None:
        logger.warning(f"No watermark found for table '{table_name}'. Returning (0, None).")
        return (0, None)
    return (record.last_synced_id, record.last_synced_at)


def advance_watermark(
    db: Session,
    table_name: str,
    new_id: int,
    new_timestamp: Optional[datetime] = None,
) -> None:
    """
    Advance the watermark after a successful batch processing.

    IMPORTANT: Only call this AFTER the vector store upsert has succeeded.
    If this function is called before a successful write, a crash would cause
    data to be skipped on the next run.

    Args:
        db: Active database session.
        table_name: Name of the source table.
        new_id: The highest ID that was successfully processed in this batch.
        new_timestamp: Optional timestamp to record. Defaults to now.
    """
    if new_timestamp is None:
        new_timestamp = datetime.utcnow()

    record = db.query(SyncState).filter(SyncState.table_name == table_name).first()
    if record is None:
        logger.error(f"Cannot advance watermark: no entry for table '{table_name}'.")
        raise ValueError(f"No sync_state entry for table '{table_name}'")

    old_id = record.last_synced_id
    record.last_synced_id = new_id
    record.last_synced_at = new_timestamp
    record.sync_status = "IDLE"
    record.updated_at = datetime.utcnow()

    db.commit()
    logger.info(
        f"Watermark advanced for '{table_name}': {old_id} -> {new_id}"
    )


def set_sync_status(db: Session, table_name: str, status: str) -> None:
    """
    Update the sync status for a table (e.g., 'RUNNING', 'FAILED', 'IDLE').

    Used at the start of a pipeline run to mark a table as 'RUNNING',
    and at the end to mark it 'IDLE' or 'FAILED'.

    Args:
        db: Active database session.
        table_name: Name of the source table.
        status: New status string.
    """
    record = db.query(SyncState).filter(SyncState.table_name == table_name).first()
    if record is None:
        logger.error(f"Cannot set status: no entry for table '{table_name}'.")
        raise ValueError(f"No sync_state entry for table '{table_name}'")

    record.sync_status = status
    record.updated_at = datetime.utcnow()
    db.commit()
    logger.info(f"Sync status for '{table_name}' set to '{status}'.")


def get_all_watermarks(db: Session) -> List[SyncState]:
    """
    Return all watermark records. Useful for dashboard/monitoring endpoints.
    """
    return db.query(SyncState).all()
