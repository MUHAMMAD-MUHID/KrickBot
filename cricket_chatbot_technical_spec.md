# Technical Specification: Self-Updating Cricket Analytics Chatbot

**Purpose of this document:** This is a complete implementation reference. An engineer or coding agent should be able to build the system directly from this document without needing further clarification on the core architecture.

---

## 1. Problem Statement

We have a MariaDB database containing cricket data (players, teams, matches, ball-by-ball events, statistics, tournaments). New rows are added to this database daily as new matches happen.

We need a chatbot that:

1. Answers natural-language questions about this data (factual stats, comparisons, explanations, summaries).
2. Automatically incorporates newly added data without manual intervention.
3. Never requires full model retraining as part of the daily update cycle.
4. Gives numerically accurate answers for factual queries, and rich, natural-language answers for explanatory/comparative queries.
5. Scales efficiently as the database grows — the update mechanism must not become slower or more expensive over time.

---

## 2. Design Principle

Separate **"how to talk"** from **"what is currently true."**

| Concern | Handled by | Update frequency |
|---|---|---|
| Language ability, reasoning style, domain vocabulary | Fine-tuned LLM | Rare (weeks/months) |
| Current facts (today's data) | Vector DB (RAG) + direct DB queries | Continuous (daily / real-time) |

The LLM is never the source of truth for facts. It is only the source of truth for *how to phrase and reason about* facts it's given at query time.

---

## 3. High-Level Architecture

```
                         ┌─────────────────────────┐
                         │        MariaDB           │  ← single source of truth
                         │  (players, matches, etc) │
                         └────────────┬─────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                          │
     ┌───────────▼────────────┐              ┌──────────────▼─────────────┐
     │   UPDATE PIPELINE       │              │      QUERY PIPELINE        │
     │  (runs on schedule/CDC) │              │   (runs per user question) │
     └───────────┬────────────┘              └──────────────┬─────────────┘
                 │                                           │
     1. Watermark tracker                        1. Intent router (LLM call)
     2. Delta extractor                                     │
     3. Document generator                     ┌────────────┴────────────┐
     4. Embedding + upsert                      │                        │
                 │                        [Factual/numeric]      [Explanatory/comparative]
                 ▼                              │                        │
       ┌───────────────────┐              Text-to-SQL              Vector search
       │   Vector Database   │◄─────────────────┘  query DB directly│ (RAG retrieval)
       └───────────────────┘                              │                │
                                                            └───────┬────────┘
                                                                    ▼
                                                        Fine-tuned LLM
                                                     (combines retrieved
                                                      facts + generates
                                                      natural-language answer)
                                                                    │
                                                                    ▼
                                                              Final Answer
```

---

## 4. Update Pipeline (Daily / Continuous Self-Update)

### 4.1 Goal
Keep the knowledge base current without reprocessing the entire database each run.

### 4.2 Components

**a) Watermark Tracker**
A small metadata table, e.g.:

```sql
CREATE TABLE sync_state (
    table_name VARCHAR(50) PRIMARY KEY,
    last_synced_id BIGINT,
    last_synced_at DATETIME
);
```

Each table being synced (Matches, Batting, Bowling, BallByBall, etc.) has its own watermark row. On every run, the pipeline queries:

```sql
SELECT * FROM Matches WHERE MatchID > (SELECT last_synced_id FROM sync_state WHERE table_name='Matches');
```

This guarantees the pipeline only ever processes new/changed rows — cost stays flat regardless of total database size.

**Two implementation options:**

| Option | How it works | When to use |
|---|---|---|
| Scheduled polling (simple) | A cron job runs on a fixed interval (e.g. every night, or every hour) and checks for new rows since the watermark | Good default. Simple to build and debug. Fine for daily-match-level freshness. |
| Change Data Capture / CDC (advanced) | A tool (e.g. Debezium) listens to MariaDB's binary log and emits an event the instant a row is inserted/updated | Use if you need near real-time updates (e.g. ball-by-ball updates during a live match) |

Start with scheduled polling. Move to CDC only if the product requirement demands live/in-match updates.

**b) Delta Extractor**
Pulls only the rows returned by the watermark query above — never a full table scan.

**c) Document Generator**
Converts each new/changed row into a natural-language document, exactly as already planned in the project's document generation logic (Player Documents, Match Documents, Tournament Documents, Comparison Documents, etc.). Runs only on the delta set.

**d) Embedding + Upsert**
Each generated document must have a **deterministic, stable ID**, for example:

```
player_summary::{player_id}
match_summary::{match_id}
tournament_summary::{tournament_id}::{season}
```

When new data changes an existing fact (e.g., Babar Azam's total runs increase after a new match), the pipeline **re-embeds and overwrites** the existing vector entry using the same ID — it does not insert a duplicate. This is critical: without stable IDs, the vector DB accumulates multiple conflicting versions of the same fact over time, and retrieval can surface a stale one.

**e) Update the Watermark**
Only after a batch has been successfully embedded and stored, update `last_synced_id` / `last_synced_at`. If the pipeline fails midway, the watermark stays at the last successful point, so the next run safely retries the same batch (idempotent by design because of the stable-ID upsert).

### 4.3 Suggested Update Frequency
- Player/team/tournament summary documents: once daily (batch, after each day's matches conclude)
- Match summary documents: once per completed match
- Ball-by-ball documents (if used): can be generated live if near real-time detail is required, otherwise batched with match summaries

### 4.4 Why This Is Efficient and Robust
- **Efficient:** cost of each run is proportional to *new* data only, not total data. A database with 10 million rows costs the same to update daily as one with 10 thousand.
- **Robust:** idempotent (safe to re-run), no duplicate/stale facts (stable IDs), failure-safe (watermark only advances on success), no model retraining in the loop (so no downtime, no GPU cost, no risk of degrading the model's language ability).

---

## 5. Query Pipeline (What Happens When a User Asks a Question)

### 5.1 Step 1 — Intent Routing
A lightweight LLM call (or a simple classifier) categorizes the incoming question into one of two buckets:

- **Factual/numeric** — e.g. "How many centuries has Babar Azam scored?", "What was the score in the last over?"
- **Explanatory/comparative/narrative** — e.g. "Why is Babar Azam considered great?", "Compare Shaheen Afridi and Haris Rauf", "Explain Pakistan's win against Australia"

### 5.2 Step 2a — Factual Path: Text-to-SQL
For factual/numeric questions, the LLM generates a SQL query against MariaDB directly (using the known schema) and executes it to get the **exact** value. This avoids relying on approximate vector similarity search for numbers that must be precise.

Safeguards to build in:
- Only allow generated queries to run against a read-only database user/connection.
- Validate the generated SQL against an allow-list of tables/columns before execution.
- Set a query timeout and row-limit to prevent runaway queries.

### 5.3 Step 2b — Explanatory Path: RAG Retrieval
For narrative/comparative questions, the system embeds the user's question, searches the vector database for the most relevant documents (player summaries, match summaries, comparison documents, etc.), and retrieves the top matches.

Recommended retrieval improvements over "plain" vector search:
- **Hybrid search:** combine keyword search (e.g. BM25) with vector similarity — helps when the question contains exact names or numbers.
- **Metadata filtering:** tag every document with structured metadata (player_id, team, tournament, season, date) so retrieval can be narrowed before similarity search runs (e.g., restrict to "PSL 2025" documents).
- **Reranking:** after retrieving the top-k candidates, use a cross-encoder reranker to reorder them by true relevance before passing to the LLM.

### 5.4 Step 3 — Response Generation
The fine-tuned LLM receives:
- The user's original question
- Either the SQL query result (factual path) or the retrieved documents (explanatory path)

...and generates the final natural-language response. This is the only place the LLM "writes" — it never invents facts; it explains facts it was handed.

### 5.5 Optional Step 4 — Self-Check (Corrective RAG pattern)
Before returning the answer, an optional lightweight check: does the generated answer's numeric claims match the retrieved/queried data? If not, either re-retrieve or flag low confidence. This catches hallucination before it reaches the user.

---

## 6. One-Time (Rare) Fine-Tuning Process

This does **not** run as part of the daily update cycle. It runs only when you want to improve the model's general reasoning/language ability (e.g., every few weeks/months, or when you notice systematic quality issues).

1. Generate a Question-Answer instruction dataset from historical cricket documents (already covered in the project's existing plan).
2. Fine-tune the base Llama model on this dataset to teach cricket terminology, comparison style, explanation style.
3. Deploy the updated model. The vector DB and MariaDB connection remain unchanged — freshness of facts is untouched by this process.

---

## 7. Technology Stack Recommendations

| Layer | Suggested tools |
|---|---|
| Source database | MariaDB (existing) |
| Watermark/orchestration | Python script + cron, or Airflow for more complex scheduling |
| CDC (if needed later) | Debezium + Kafka (or MariaDB's built-in binlog tools) |
| Embedding model | Any open-source sentence embedding model (e.g. BGE, E5) or an API-based embedding model |
| Vector database | Qdrant, Milvus, Weaviate, or pgvector (Postgres extension) — all support upsert by ID |
| Reranker (optional) | A cross-encoder model (e.g. BGE-reranker) |
| Text-to-SQL | The fine-tuned LLM itself, or a smaller dedicated model, given the known schema as context |
| LLM serving | Self-hosted Llama (as already planned) via a local inference server |

---

## 8. Implementation Task Breakdown

1. **Schema & watermark setup** — create `sync_state` table, decide sync granularity per table.
2. **Document generator** — implement/extend the row-to-text conversion logic; ensure every generated document has a stable, deterministic ID.
3. **Update pipeline script** — implement the watermark-based delta extraction → document generation → embedding → upsert loop; wrap in a cron job.
4. **Vector database setup** — choose and deploy a vector DB; define metadata schema (player_id, team, tournament, season, date, doc_type).
5. **Intent router** — implement the classification step (factual vs. explanatory).
6. **Text-to-SQL module** — implement schema-aware SQL generation with a read-only DB connection, validation, and timeouts.
7. **RAG retrieval module** — implement hybrid search + metadata filtering + optional reranking.
8. **Response generation** — wire retrieved context (SQL result or documents) into the fine-tuned LLM's prompt.
9. **(Optional) Self-check step** — validate generated numeric claims against source data before returning the response.
10. **Fine-tuning pipeline** — separate, offline process; not part of the daily loop.
11. **Testing** — unit tests for the update pipeline's idempotency (re-running a batch should not create duplicates), and evaluation tests for answer accuracy on factual questions.

---

## 9. Key Robustness Rules (Do Not Skip)

- Every generated document must have a **deterministic ID** — never auto-generate random IDs, or duplicates will accumulate.
- The update pipeline must be **idempotent** — safe to re-run on the same data without side effects.
- The watermark must only advance **after** a successful write to the vector DB, not before.
- Factual/numeric answers should be sourced from **direct database queries**, not from vector search, whenever exact precision matters.
- The LLM must never be the only source of truth for a fact — it should always be handed the fact and asked to explain it, not asked to recall it.
- Full model retraining should never be part of the daily/automated update loop.

---

## 10. Summary

- **Freshness** comes from a lightweight, incremental update pipeline that only processes new rows, keyed to a watermark, writing into a vector database with stable, upsertable document IDs.
- **Accuracy** comes from splitting queries into a factual path (direct SQL) and an explanatory path (RAG), so the system never guesses at a number it can just look up.
- **Efficiency** comes from never reprocessing old data and never retraining the model as part of routine updates.
- **The model itself stays fixed** most of the time; only the data around it changes. This is what makes the whole system scalable and low-maintenance.
