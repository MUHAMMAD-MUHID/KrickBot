"""
Update Pipeline Orchestrator

This script is meant to be run on a schedule (e.g., daily cron job).
It iterates over all tracked tables, finds new rows since the last watermark,
generates text documents, and upserts them to the vector store.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.utils.logger import get_logger
from app.update_pipeline.watermark import get_watermark, advance_watermark, set_sync_status
from app.update_pipeline.delta_extractor import extract_delta_rows, TRACKING_COLUMNS
from app.update_pipeline.document_generator import generate_documents_from_rows
from app.update_pipeline.embedder import embed_and_upsert

logger = get_logger(__name__)

BATCH_SIZE = 100

def run_pipeline():
    logger.info("=" * 60)
    logger.info("Starting KrickBot Update Pipeline")
    logger.info("=" * 60)

    db = SessionLocal()
    try:
        for table_name, tracking_col in TRACKING_COLUMNS.items():
            logger.info(f"\n--- Processing Table: {table_name} ---")
            
            try:
                # 1. Lock the table
                set_sync_status(db, table_name, "RUNNING")
                
                total_processed = 0
                while True:
                    # 2. Get current watermark
                    last_id, _ = get_watermark(db, table_name)
                    
                    # 3. Extract delta
                    rows = extract_delta_rows(db, table_name, last_id, batch_size=BATCH_SIZE)
                    
                    if not rows:
                        logger.info(f"No new rows to process for {table_name}. Up to date.")
                        break
                        
                    # 4. Generate documents
                    docs = generate_documents_from_rows(table_name, rows)
                    
                    # 5. Embed and Upsert
                    success = embed_and_upsert(docs)
                    
                    if not success:
                        raise RuntimeError(f"Failed to embed/upsert documents for {table_name}")
                        
                    # 6. Advance watermark (using the highest tracking_col value in the batch)
                    new_last_id = max(row[tracking_col] for row in rows)
                    advance_watermark(db, table_name, new_last_id)
                    
                    total_processed += len(rows)
                    logger.info(f"Successfully processed batch. Advanced watermark to {new_last_id}")
                    
                logger.info(f"[OK] Completed {table_name}. Total rows processed: {total_processed}")
                
                # 7. Unlock the table
                set_sync_status(db, table_name, "IDLE")

            except Exception as e:
                # On failure, unlock with FAILED status and continue to next table
                logger.error(f"[FAIL] Error processing table {table_name}: {e}")
                set_sync_status(db, table_name, "FAILED")
                # We continue to the next table even if one fails

    except Exception as e:
        logger.error(f"Pipeline crashed catastrophically: {e}")
    finally:
        db.close()
        
    logger.info("=" * 60)
    logger.info("Pipeline run complete.")
    logger.info("=" * 60)

if __name__ == "__main__":
    run_pipeline()
