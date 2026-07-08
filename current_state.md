# KrickBot — Change History Log

> **Purpose**: This file tracks every change made to the codebase, what was changed, why, and when. Share this file along with the code to give any LLM or developer full context of the project's history and current state.

---

## Project Overview

**KrickBot** is an AI-Powered Cricket Analytics Chatbot with a Self-Updating Knowledge Base. It connects to a MariaDB database containing cricket data (players, teams, matches, ball-by-ball events, tournaments) and answers user questions in plain English using a combination of:

- **Direct SQL queries** for factual/numeric questions (exact precision)
- **RAG (Retrieval-Augmented Generation)** for explanatory/comparative questions
- **A self-updating knowledge base** that stays current with daily data without model retraining

### Architecture (Two Independent Pipelines)

1. **Update Pipeline** (runs daily): Watermark tracker → Delta extractor → Document generator → Embedding & upsert to vector store
2. **Query Pipeline** (runs per user question): Intent router → Factual path (Text-to-SQL) or Explanatory path (RAG) → Response generation via fine-tuned LLM

### Technology Stack

| Component | Technology |
|---|---|
| Language | Python 3.14 |
| Web Framework | FastAPI 0.115.0 |
| Database | MariaDB 12.3.2 (localhost:3306) |
| ORM | SQLAlchemy 2.0.35 |
| DB Driver | PyMySQL 1.1.1 |
| Vector Store | MariaDB native VECTOR columns (planned) |
| Embedding Model | Open-source BGE/E5 (planned, local) |
| LLM | Self-hosted Llama (planned, not yet installed) |
| Config | python-dotenv 1.0.1 |

### Design Documents

- `Cricket_Chatbot_Solution_Design.md` — High-level solution design
- `cricket_chatbot_technical_spec.md` — Detailed technical specification
- `schema.sql` — Full MariaDB schema dump (krickbot database)

---

## Change Log

### [2026-07-08] Task 1: Project Structure & Watermark Setup

**Status**: ✅ Complete

#### What was done

1. **Created project directory structure**
   - `app/` — Main application package
   - `app/models/` — SQLAlchemy ORM models
   - `app/update_pipeline/` — Daily update pipeline components
   - `app/query_pipeline/` — Per-question query pipeline components
   - `app/utils/` — Shared utilities (logging, etc.)
   - `scripts/` — One-time setup/migration scripts
   - `tests/` — Test suite (empty, ready for future tests)

2. **Created configuration layer** (`app/config.py`)
   - Loads environment variables from `.env` file
   - Exposes typed `Settings` class with DB credentials, server config, log level
   - Builds SQLAlchemy DATABASE_URL with `pymysql` driver and `utf8mb4` charset
   - Why utf8mb4: The database contains Urdu text (articles table) that needs full Unicode support

3. **Created database connection layer** (`app/database.py`)
   - Synchronous SQLAlchemy engine (not async — simpler for our batch + API workload)
   - Connection pool: `pool_size=5`, `max_overflow=10`, `pool_recycle=3600`
   - Why pool_recycle=3600: Prevents MariaDB from closing idle connections (its default `wait_timeout` is 28800s, but recycling at 1hr is a safety margin)
   - `get_db()` — FastAPI dependency injection for database sessions
   - `check_db_connection()` — Health check function

4. **Created logging module** (`app/utils/logger.py`)
   - Centralized logger factory with consistent format: `[timestamp] [level] [module] message`
   - Outputs to stdout (not stderr) for easy container/cloud log capture
   - Log level configurable via `LOG_LEVEL` env var

5. **Created SyncState ORM model** (`app/models/sync_state.py`)
   - Maps to `sync_state` table in MariaDB
   - Columns: `table_name` (PK), `last_synced_id`, `last_synced_at`, `sync_status`, `updated_at`
   - `sync_status` field prevents concurrent pipeline runs (IDLE/RUNNING/FAILED)
   - Why deterministic IDs: The technical spec requires watermarks to only advance after successful vector writes (idempotency rule)

6. **Created watermark operations** (`app/update_pipeline/watermark.py`)
   - `get_watermark(db, table_name)` — Read current watermark cursor
   - `advance_watermark(db, table_name, new_id)` — Move cursor forward (only after successful upsert)
   - `set_sync_status(db, table_name, status)` — Lock/unlock table for pipeline runs
   - `get_all_watermarks(db)` — List all watermarks (for monitoring)

7. **Created FastAPI application** (`app/main.py`)
   - `GET /health` — Returns `{"status": "ok", "database": "connected", "version": "0.1.0"}`
   - `GET /sync/status` — Returns all watermark states for monitoring
   - Startup event verifies DB connectivity

8. **Created migration script** (`scripts/create_sync_state.py`)
   - Creates `sync_state` table via SQLAlchemy metadata
   - Seeds 11 watermark rows for core cricket tables:
     `matches`, `batting_detail`, `bowling_detail`, `innings`, `ball_by_ball`,
     `batting_stats`, `bowling_stats`, `player`, `team`, `tournament`, `fow`
   - Idempotent — safe to re-run (skips existing rows)

9. **Created placeholder files** for future pipeline modules:
   - `app/update_pipeline/delta_extractor.py` (Task 2)
   - `app/update_pipeline/document_generator.py` (Task 2)
   - `app/update_pipeline/embedder.py` (Task 4)
   - `app/query_pipeline/intent_router.py` (Task 5)
   - `app/query_pipeline/text_to_sql.py` (Task 6)
   - `app/query_pipeline/rag_retriever.py` (Task 7)
   - `app/query_pipeline/response_generator.py` (Task 8)

10. **Created project configuration files**
    - `.env` — Environment variables (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, etc.)
    - `.env.example` — Template for .env
    - `requirements.txt` — Python dependencies

#### Bug Fixes During Implementation

- **MariaDB auth plugin issue**: MariaDB 12.3.2 defaults to `auth_gssapi_client` authentication, which PyMySQL doesn't support. Fixed by using the root password (`smart123`) which falls back to `mysql_native_password`.
- **Unicode encoding on Windows**: The `✓` and `✗` characters caused `UnicodeEncodeError` on Windows cp1252 console. Replaced with ASCII `[OK]` and `[FAIL]` in all log messages.

#### Verification Results

| Test | Result |
|---|---|
| `python -m scripts.create_sync_state` | ✅ sync_state table created with 11 rows |
| `GET /health` | ✅ `{"status": "ok", "database": "connected", "version": "0.1.0"}` |
| `GET /sync/status` | ✅ Returns all 11 watermarks with status IDLE |
| Re-run migration (idempotency) | ✅ Skips existing rows, no errors |

### [2026-07-08] Task 2: Document Generator

**Status**: ✅ Complete

#### What was done

1. **Created Delta Extractor** (`app/update_pipeline/delta_extractor.py`)
   - Implemented `extract_delta_rows()` to query database for newly added rows.
   - Mapped tables to their tracking high-water mark columns (e.g., `matches` -> `MatchNo`, `player` -> `PlayerId`).
   - Mapped composite-key scorecard tables (`batting_detail`, `bowling_detail`) to `MatchNo` since they are inserted match-by-match.
   
2. **Created Document Generator** (`app/update_pipeline/document_generator.py`)
   - Designed a `Document` dataclass to hold `doc_id`, `content`, and `metadata`.
   - Built generation functions that convert raw DB dictionary rows into natural-language paragraphs.
   - Ensured all generated documents have **deterministic IDs** (e.g., `batting_perf::{match}_{innings}_{player}`) so vector stores overwrite rather than duplicate.

3. **Created Test Script** (`scripts/test_doc_generator.py`)
   - A local script to verify extraction and generation logic against real MariaDB rows without updating watermarks.

#### Verification Results

| Test | Result |
|---|---|
| `test_doc_generator.py` | ✅ Successfully queried 0-watermark rows and produced clean, human-readable paragraphs. ID formats are verified deterministic. |

### [2026-07-08] Task 3: Update Pipeline Script

**Status**: ✅ Complete

#### What was done

1. **Created Orchestrator Script** (`scripts/run_update_pipeline.py`)
   - Implemented the core data extraction loop to process all configured tracking tables.
   - For each table, sets `sync_status` to `RUNNING`, reads `last_id`, extracts new rows, and generates documents in configurable batches of 100.
   - Advances the watermark safely *only* after documents are processed successfully.
   - Implemented graceful error handling (marks status `FAILED` on exception and continues to next table).
   
2. **Created Mock Embedder** (`app/update_pipeline/embedder.py`)
   - Added placeholder `embed_and_upsert` function returning success, ready to be wired into real vector search logic in Task 4.

3. **Fixed Unicode Logging Error** (`app/update_pipeline/watermark.py`)
   - Changed `→` to `->` to avoid `cp1252` encoding errors on the Windows console during watermark logging.

#### Verification Results

| Test | Result |
|---|---|
| Initial Pipeline Run | ✅ Successfully extracted thousands of rows across 11 tables, mocked the upsert, and correctly advanced all watermarks to their latest database ID. |
| Idempotency Run | ✅ Ran pipeline a second time immediately after; 0 rows extracted across all tables. Watermarks locked and unlocked successfully. |

---

## Current File Structure

```
KrickBot/
├── app/
│   ├── __init__.py
│   ├── config.py                   # Configuration loader (.env → typed settings)
│   ├── database.py                 # SQLAlchemy engine, session factory, health check
│   ├── main.py                     # FastAPI entry point (health, sync/status endpoints)
│   ├── models/
│   │   ├── __init__.py
│   │   └── sync_state.py           # SyncState ORM model (watermark tracker)
│   ├── update_pipeline/
│   │   ├── __init__.py
│   │   ├── watermark.py            # Watermark read/write operations
│   │   ├── delta_extractor.py      # Extracts new DB rows via watermarks
│   │   ├── document_generator.py   # Row-to-text converters
│   │   └── embedder.py             # Mock upsert (Task 4)
│   ├── query_pipeline/
│   │   ├── __init__.py
│   │   ├── intent_router.py        # [PLACEHOLDER] Task 5
│   │   ├── text_to_sql.py          # [PLACEHOLDER] Task 6
│   │   ├── rag_retriever.py        # [PLACEHOLDER] Task 7
│   │   └── response_generator.py   # [PLACEHOLDER] Task 8
│   └── utils/
│       ├── __init__.py
│       └── logger.py               # Centralized logging factory
├── scripts/
│   ├── create_sync_state.py        # Migration: create & seed sync_state table
│   ├── run_update_pipeline.py      # Main orchestrator (runs doc gen loop)
│   └── test_doc_generator.py       # Test script for extraction/generation
├── tests/
│   └── __init__.py
├── .env                            # Environment variables (has DB password)
├── .env.example                    # Template for .env
├── requirements.txt                # Python dependencies
├── current_state.md                # THIS FILE — change history
├── README.md                       # Project overview
├── Cricket_Chatbot_Solution_Design.md   # Solution design doc
├── cricket_chatbot_technical_spec.md    # Technical specification
└── schema.sql                           # MariaDB schema dump
```

---

## Next Steps (Upcoming Tasks)

| Task | Description | Status |
|---|---|---|
| Task 2 | Document Generator — row-to-text conversion logic with deterministic IDs | ✅ Complete | 
| Task 3 | Update Pipeline Script — watermark-based delta → doc gen → embed → upsert loop | ✅ Complete |
| Task 4 | Vector Database Setup — MariaDB VECTOR columns, metadata schema | 🔜 Next |
| Task 5 | Intent Router — factual vs explanatory classification | Pending |
| Task 6 | Text-to-SQL — schema-aware SQL generation with safeguards | Pending |
| Task 7 | RAG Retrieval — hybrid search + metadata filtering + reranking | Pending |
| Task 8 | Response Generation — wire context into fine-tuned LLM | Pending |
| Task 9 | Self-Check (optional) — validate numeric claims before responding | Pending |
| Task 10 | Fine-Tuning Pipeline — offline LLM training process | Pending |
| Task 11 | Testing — idempotency tests, accuracy evaluation | Pending |
