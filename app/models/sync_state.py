"""
SyncState ORM model — the watermark tracker.

This table tracks the last-processed row for each source table in the cricket
database. The update pipeline reads watermarks before extracting deltas, and
advances them only after a successful upsert to the vector store.

Key design rule (from technical spec Section 9):
  "The watermark must only advance AFTER a successful write to the vector DB,
   not before."

This ensures idempotency — if the pipeline crashes mid-batch, the watermark
stays at the last successful point, and the next run safely retries.
"""

from datetime import datetime
from sqlalchemy import Column, String, BigInteger, DateTime
from app.database import Base


class SyncState(Base):
    """
    Tracks sync progress per source table.

    Columns:
        table_name:     Primary key. Name of the source table being tracked
                        (e.g., 'matches', 'batting_detail', 'player').
        last_synced_id: The highest primary-key ID that was successfully processed.
                        The delta extractor queries: WHERE id > last_synced_id.
        last_synced_at: Timestamp of the last successful sync run.
                        Informational — the actual cursor is last_synced_id.
        sync_status:    Current state: 'IDLE', 'RUNNING', 'FAILED'.
                        Prevents concurrent pipeline runs from overlapping.
        updated_at:     Auto-updated timestamp for auditing.
    """

    __tablename__ = "sync_state"

    table_name = Column(String(50), primary_key=True)
    last_synced_id = Column(BigInteger, default=0, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    sync_status = Column(String(20), default="IDLE", nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<SyncState(table={self.table_name}, "
            f"last_id={self.last_synced_id}, "
            f"status={self.sync_status})>"
        )
