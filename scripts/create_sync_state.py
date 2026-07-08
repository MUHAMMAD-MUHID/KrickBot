"""
Database migration script: Create and seed the sync_state table.

Run this script once to set up the watermark tracking table.
It is safe to re-run — it uses CREATE TABLE IF NOT EXISTS and
INSERT IGNORE to avoid duplicates.

Usage:
    python -m scripts.create_sync_state

What it does:
1. Creates the sync_state table if it doesn't exist
2. Seeds it with watermark rows for all core cricket tables
3. Verifies the table was created and seeded correctly
"""

import sys
import os

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.sync_state import SyncState, Base
from app.utils.logger import get_logger

logger = get_logger(__name__)

# --- Tables to track ---
# These are the core cricket tables whose data feeds the update pipeline.
# Each gets a watermark row so the delta extractor knows where it left off.
TRACKED_TABLES = [
    "matches",          # Match results, scores, winners
    "batting_detail",   # Per-match batting scorecards
    "bowling_detail",   # Per-match bowling scorecards
    "innings",          # Innings-level scores and overs
    "ball_by_ball",     # Ball-level detail (optional, for deep analysis)
    "batting_stats",    # Aggregated batting stats per player/season
    "bowling_stats",    # Aggregated bowling stats per player/season
    "player",           # Player profiles (name, DOB, role, style)
    "team",             # Team metadata
    "tournament",       # Tournament metadata
    "fow",              # Fall of wickets
]


def run_migration():
    """Create the sync_state table and seed it with tracked tables."""

    logger.info("=" * 60)
    logger.info("Running migration: create_sync_state")
    logger.info("=" * 60)

    # Step 1: Create the table using SQLAlchemy's metadata
    logger.info("Step 1: Creating sync_state table (if not exists)...")
    Base.metadata.create_all(bind=engine, tables=[SyncState.__table__])
    logger.info("[OK] sync_state table ready.")

    # Step 2: Seed watermark rows
    logger.info(f"Step 2: Seeding {len(TRACKED_TABLES)} watermark rows...")
    db = SessionLocal()
    try:
        for table_name in TRACKED_TABLES:
            # Check if row already exists (safe to re-run)
            existing = db.query(SyncState).filter(
                SyncState.table_name == table_name
            ).first()

            if existing is None:
                new_entry = SyncState(
                    table_name=table_name,
                    last_synced_id=0,
                    last_synced_at=None,
                    sync_status="IDLE",
                )
                db.add(new_entry)
                logger.info(f"  + Added watermark for '{table_name}'")
            else:
                logger.info(f"  ○ Watermark for '{table_name}' already exists (skipped)")

        db.commit()
        logger.info("[OK] All watermark rows seeded.")

    except Exception as e:
        db.rollback()
        logger.error(f"[FAIL] Migration failed: {e}")
        raise
    finally:
        db.close()

    # Step 3: Verify
    logger.info("Step 3: Verifying...")
    db = SessionLocal()
    try:
        count = db.query(SyncState).count()
        logger.info(f"[OK] sync_state table has {count} rows.")

        all_records = db.query(SyncState).all()
        for record in all_records:
            logger.info(f"  {record}")

    finally:
        db.close()

    logger.info("=" * 60)
    logger.info("Migration complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_migration()
