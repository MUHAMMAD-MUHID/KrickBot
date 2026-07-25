"""
Context Formatter — transforms raw pipeline outputs into clean LLM-ready context.

This module sits between the data retrieval layer (Text-to-SQL / RAG) and the
response generator. Its job is to:
1. Remove all implementation details (SQL queries, internal column names)
2. Classify the result shape (single_stat, multi_stat, comparison, no_data, error)
3. Produce a compact, human-readable data block the LLM can reference directly

The response generator's system prompt references these result_type hints to
select the appropriate formatting template (single sentence vs table vs narrative).
"""

import json
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ─── Result type constants ───────────────────────────────────────────

SINGLE_STAT = "single_stat"
MULTI_STAT = "multi_stat"
COMPARISON = "comparison"
NO_DATA = "no_data"
ERROR = "error"


def classify_result(rows: list[dict], user_query: str = "") -> str:
    """
    Determine the result shape so the LLM can pick the right response template.

    - 0 rows           -> NO_DATA
    - error dict       -> ERROR
    - 1 row, 1-2 cols  -> SINGLE_STAT
    - 1 row, 3+ cols   -> MULTI_STAT (player profile style)
    - 2+ rows          -> MULTI_STAT or COMPARISON

    Heuristic for comparison: if the query mentions "vs", "compare", or
    "against" and we got 2+ rows with a name-like first column, treat it
    as a comparison.
    """
    if not rows:
        return NO_DATA

    # Check for error rows
    if len(rows) == 1 and "error" in rows[0]:
        return ERROR

    lower_query = user_query.lower()
    comparison_keywords = ["vs", "versus", "compare", "comparison", "against", "head to head"]

    if len(rows) >= 2 and any(kw in lower_query for kw in comparison_keywords):
        return COMPARISON

    if len(rows) == 1:
        num_cols = len(rows[0])
        return SINGLE_STAT if num_cols <= 2 else MULTI_STAT

    return MULTI_STAT


def _humanize_key(key: str) -> str:
    """
    Convert a database column name into a human-readable label.
    e.g. 'BatsmanName' -> 'Batsman Name', 'SR' -> 'SR', 'total_wickets' -> 'Total Wickets'
    """
    import re
    # Handle snake_case
    label = key.replace("_", " ")
    # Handle CamelCase — insert space before uppercase letters
    label = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", label)
    return label.title()


def _format_value(value) -> str:
    """Format a single value for display — numbers, decimals, None handling."""
    if value is None:
        return "N/A"
    if isinstance(value, float):
        # Batting average / strike rate: 2 decimal places
        # Economy: 1-2 decimals — we'll use 2 for consistency
        return f"{value:.2f}"
    return str(value)


def format_factual_context(sql_result: dict, user_query: str = "") -> str:
    """
    Format a FACTUAL (Text-to-SQL) result into a clean context block.

    Input:  {"query": "...", "sql": "SELECT ...", "results": [...], "error": "..."}
    Output: A structured string the LLM receives as its only data source.
            SQL query is NEVER included.
    """
    # Handle errors first
    if sql_result.get("error"):
        error_msg = sql_result["error"]
        return json.dumps({
            "result_type": ERROR,
            "message": f"Database error: {error_msg}"
        }, indent=2)

    rows = sql_result.get("results", [])

    # Handle error rows from execute_sql
    if rows and len(rows) == 1 and "error" in rows[0]:
        return json.dumps({
            "result_type": ERROR,
            "message": rows[0]["error"]
        }, indent=2)

    result_type = classify_result(rows, user_query)

    if result_type == NO_DATA:
        return json.dumps({
            "result_type": NO_DATA,
            "message": "No matching records found in the database for this query.",
            "row_count": 0
        }, indent=2)

    # Build clean data rows with human-readable keys
    clean_rows = []
    for row in rows:
        clean_row = {}
        for key, value in row.items():
            clean_row[_humanize_key(key)] = _format_value(value)
        clean_rows.append(clean_row)

    context = {
        "result_type": result_type,
        "row_count": len(clean_rows),
        "data": clean_rows
    }

    return json.dumps(context, indent=2)


def format_explanatory_context(retrieved_docs: list[dict] | str) -> str:
    """
    Format EXPLANATORY (RAG) retrieved documents into a clean context block.

    Accepts either:
    - A list of dicts with 'content' and optional 'metadata' keys
    - A plain string (fallback message)
    """
    if isinstance(retrieved_docs, str):
        return json.dumps({
            "result_type": NO_DATA if "not" in retrieved_docs.lower() else "narrative",
            "message": retrieved_docs,
            "doc_count": 0
        }, indent=2)

    if not retrieved_docs:
        return json.dumps({
            "result_type": NO_DATA,
            "message": "No relevant documents found in the knowledge base for this query.",
            "doc_count": 0
        }, indent=2)

    docs = []
    for doc in retrieved_docs:
        entry = {"content": doc.get("content", "")}
        meta = doc.get("metadata")
        if meta:
            # Include useful metadata (match reference, format, etc.)
            entry["source"] = meta
        docs.append(entry)

    return json.dumps({
        "result_type": "narrative",
        "doc_count": len(docs),
        "documents": docs
    }, indent=2)


def format_chitchat_context() -> str:
    """Minimal context for chitchat — the LLM uses its cricket persona."""
    return json.dumps({
        "result_type": "chitchat",
        "message": "This is a casual greeting or conversation. Respond as KrickBot with your cricket personality."
    }, indent=2)
