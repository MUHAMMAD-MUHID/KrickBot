"""
Database migration script: Create vector_store table.

Run this script once to create the vector_store table.
MariaDB 12.3 supports the native VECTOR data type.
"""

import sys
import os
import sqlalchemy

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine
from app.utils.logger import get_logger

logger = get_logger(__name__)

def run_migration():
    logger.info("=" * 60)
    logger.info("Running migration: create_vector_store")
    logger.info("=" * 60)

    try:
        with engine.connect() as conn:
            # Create the vector_store table
            # We use raw SQL because VECTOR is a bleeding-edge MariaDB type 
            # that might not be natively supported by standard SQLAlchemy types yet.
            logger.info("Creating vector_store table with VECTOR(384)...")
            
            # Using IF NOT EXISTS makes it idempotent
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS vector_store (
                    doc_id VARCHAR(255) PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata JSON,
                    embedding VECTOR(384) NOT NULL
                ) ENGINE=InnoDB;
            """))
            conn.commit()
            
            logger.info("[OK] vector_store table created successfully.")
            
    except sqlalchemy.exc.OperationalError as e:
        logger.error(f"[FAIL] Operational Error during migration: {e}")
        logger.error("Ensure you are running MariaDB 11.5+ or 12+ which supports VECTOR columns.")
        raise
    except Exception as e:
        logger.error(f"[FAIL] Migration failed: {e}")
        raise

    logger.info("=" * 60)
    logger.info("Migration complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_migration()
