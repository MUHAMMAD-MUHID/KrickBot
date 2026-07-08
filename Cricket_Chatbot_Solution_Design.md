Proposed Solution Design

Team (AI)

Muhammad Muhid

Ali Bin Mohsin

Hafiz Muhammad Abu Huraira

Assigned By: Sir Istiaq Dated: 07/07/2026

AI-Powered Cricket Analytics Chatbot with a Self-Updating Knowledge Base

1.  Overview

The project owns a MariaDB database that stores cricket data ---
players, teams, matches, ball-by-ball events, and tournament records.
New matches are added to this database every day, continuously growing
the dataset. The goal is a chatbot that lets users ask questions in
plain English and receive accurate, informative answers, while
automatically staying current with newly added data --- without
requiring daily model retraining.

2.  Core Design Principle

The solution separates two responsibilities that are often incorrectly
combined into one:

How to talk: handled by a fine-tuned language model, trained once and
updated only occasionally (e.g. every few months).

What is currently true: handled by a continuously updated knowledge base
(vector database) and direct database queries.

The language model is never treated as the source of truth for facts. It
only explains facts that are retrieved and handed to it at the moment a
question is asked. This is what allows the system to stay current daily
without any retraining.

3.  Proposed Architecture

The system has two independent pipelines that run separately: an Update
Pipeline that keeps the knowledge base current, and a Query Pipeline
that answers user questions.

3.1 Update Pipeline (runs daily / on schedule)

Watermark Tracker: a small metadata table records the last processed
record ID/timestamp for each database table.

Delta Extractor: on each run, only rows added after the last watermark
are retrieved, never the full database.

Document Generator: converts each new/changed row into a readable
cricket document (player summary, match summary, comparison, etc.), as
already defined in the project's data processing design.

Embedding & Upsert: each document is given a fixed, deterministic ID
(for example player_summary: :babar_azam). When a fact changes, the
existing entry is overwritten rather than duplicated, keeping the
knowledge base accurate and free of stale records.

Watermark Update: the tracker only advances after a successful update,
making the pipeline safe to re-run if it ever fails midway.

3.2 Query Pipeline (runs per user question)

Intent Routing: each incoming question is classified as either
factual/numeric (for example "How many centuries has Babar Azam
scored?") or explanatory/comparative (like "Why is Babar Azam considered
great?").

Factual Path: the system generates a direct SQL query against MariaDB to
fetch the exact number, avoiding any approximation.

Explanatory Path: the system searches the vector knowledge base for the
most relevant documents and retrieves the top matches.

Response Generation: the fine-tuned model receives the retrieved fact(s)
and produces a clear, natural-language answer.

4.  Why This Approach Is Efficient

Efficiency comes from never reprocessing old data. Because the update
pipeline only touches rows added since the last run, the daily update
cost stays flat whether the database has ten thousand rows or ten
million. There is no daily retraining, which removes the recurring GPU
cost and downtime that a retrain-every-day approach would require.

5.  Why This Approach Is Robust

Numeric accuracy: factual answers are pulled directly from the database
rather than approximated through similarity search, removing a common
source of chatbot errors.

No stale or duplicate facts: deterministic document IDs ensure updated
facts overwrite old ones instead of accumulating conflicting versions.

Fault tolerance: the watermark-based design makes the update pipeline
idempotent; a failed run can be safely retried without side effects.

Stable language quality: because the model is not retrained daily, there
is no risk of a bad daily retrain degrading response quality.

6.  Summary Comparison: Traditional vs Proposed Approach

7.  Conclusion

This design keeps the language model fixed and lightweight to maintain,
while continuously refreshing a separate knowledge base that reflects
the latest state of the cricket database. Combined with a
factual/explanatory query router, the chatbot remains accurate on
statistics, informative on analysis, and self-updating with no manual
retraining required as new matches are added.

Intent Routing:

LLM-based classifier (handles the ambiguous cases)

When the rules don't confidently match either bucket, you make one
small, cheap LLM call whose only job is to output a category --- not to
answer the question. You force structured output so your code can act on
it reliably:

System: You are a query router for a cricket chatbot. Classify the
user's

question into exactly one category and extract any
player/team/tournament

names mentioned. Respond only in this JSON format:

{

"intent": "factual" \| "explanatory" \| "mixed",

"entities": {"players": \[...\], "teams": \[...\], "tournament": null,
"season": null},

"confidence": 0.0-1.0

}

Question: "How many centuries has Babar Azam scored in PSL?"

This costs almost nothing (it's a tiny model call with a short output),
and it's far more reliable than keyword matching for oddly-phrased
questions.

The "mixed" case --- this matters a lot in practice

Real users often ask both in one sentence: "Babar Azam has scored 6000+
runs --- what makes him so consistent?" That's a factual sub-question
and an explanatory one glued together.

The router should be allowed to say "mixed", and in that case, the query
pipeline does both: pull the exact number via SQL, retrieve explanatory
documents via RAG, and hand both to the final LLM together. Don't force
every question into a single bucket --- that's where naive routers
break.

Confidence threshold as a safety net

If the classifier's confidence is low, don't gamble --- default to
running both paths (SQL + RAG) and let the final response-generation LLM
decide what's actually relevant to include. It's slightly more expensive
per query, but far cheaper than giving a wrong or incomplete answer.

That's the shape of the decision. The core judgment call happens in one
place: the "classify intent" step. Everything else is just routing based
on that output.

A couple of things worth calling out explicitly since they trip people
up when they actually build this:

The classifier never sees the answer, only the question. It's not trying
to be smart about cricket --- it's just pattern-matching the shape of
the question (does it want a single precise value, or does it want
reasoning/narrative).

Cost matters. Keyword rules cost nothing and catch the majority of real
traffic (most cricket questions are pretty formulaic --- "how many runs
did X score in Y"). The LLM classifier only runs for the minority that
don't match a clear pattern, which keeps latency and API cost low.

Getting this wrong isn't catastrophic --- it's recoverable. If the
router picks "explanatory" for something that was actually factual, the
final response-generation LLM still sees the retrieved documents and can
often still surface the right number if it's in there; it's just less
reliable than a direct SQL lookup. That's why the "mixed → run both"
fallback exists --- it's the safety valve for a router that's
necessarily an approximation.
