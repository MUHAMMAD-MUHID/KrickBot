"""
Delta Extractor — pulls only new rows since the last watermark.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Map table names to their primary tracking column
# For composite keys, we use MatchNo as the high-water mark because scorecard rows are added per match
TRACKING_COLUMNS = {
    "matches": "MatchNo",
    "batting_detail": "MatchNo",
    "bowling_detail": "MatchNo",
    "innings": "MatchNo",
    "fow": "MatchNo",
    "ball_by_ball": "MatchNo",
    "player": "PlayerId",
    "team": "TeamId",
    "tournament": "TournamentId",
    "batting_stats": "PlayerId", 
    "bowling_stats": "PlayerId",
}

def extract_delta_rows(db: Session, table_name: str, last_id: int, batch_size: int = 100):
    """
    Extract rows from the table where the tracking column is greater than last_id.
    Returns a list of dictionaries.
    """
    if table_name not in TRACKING_COLUMNS:
        logger.error(f"Table {table_name} is not configured for delta extraction.")
        return []

    tracking_col = TRACKING_COLUMNS[table_name]
    
    # Use raw SQL to return raw dictionaries mapping directly to columns
    query = text(f"""
        SELECT * FROM {table_name} 
        WHERE {tracking_col} > :last_id 
        ORDER BY {tracking_col} ASC 
        LIMIT :batch_size
    """)
    
    result = db.execute(query, {"last_id": last_id, "batch_size": batch_size})
    rows = [dict(row._mapping) for row in result]
    
    logger.info(f"Extracted {len(rows)} delta rows from {table_name} (last_id={last_id})")
    return rows
