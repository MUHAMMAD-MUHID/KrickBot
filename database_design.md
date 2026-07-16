# KrickBot: Database Design and Dataset Generation Plan

Building a highly informative, prediction-capable, and reasoning-driven cricket bot requires a rock-solid foundation. This document outlines the step-by-step plan to design the database architecture, clean the data, and generate a high-class, overfitting/underfitting-free dataset for LLM fine-tuning.

---

## Phase 1: Database Schema Analysis & Refinement
*Objective: Ensure the MariaDB structure is optimized for both fast querying and rich data extraction.*

1. **Entity-Relationship (ER) Mapping:**
   - Map all existing tables (Players, Clubs, Matches, Innings, Bowling Figures, Tournaments, Cities, Countries, etc.).
   - Define clear Primary Keys (PKs) and Foreign Keys (FKs) across all tables to ensure referential integrity.
2. **Schema Normalization (up to 3NF):**
   - Eliminate redundant data. Instead of storing `City: Rawalpindi` alongside `City Id: 1` in a flat table, ensure they are properly joined.
3. **Indexing Strategy:**
   - Create indices on frequently queried columns (e.g., `Player Id`, `Club Id`, `Match Date`) to speed up analytical queries used for dataset generation.

## Phase 2: Data Cleaning & Standardization
*Objective: Ensure the data going into the LLM is "super clean" and human-readable, replacing raw database IDs with meaningful text.*

1. **Handle Missing and Default Values:**
   - Identify and scrub placeholder values (e.g., `0000-00-00` for DOBs, `0` for images, missing stats).
   - Decide fallback logic (e.g., outputting "Age unknown" instead of "DOB 0000").
2. **ID Resolution (Denormalization for the Model):**
   - Map all IDs (City ID, Club ID, Country ID) to their actual string names. The model should never see `Club Id: 7`; it should see `Club: Rawalpindi Royals`.
3. **Categorical Standardization:**
   - Standardize playing roles ("Wicket Keeper", "Batsman", "Allrounder") and styles ("Right Hand Batsman", "Left Arm Spin").

## Phase 3: Analytics and Feature Engineering Layer (The "Brain" of the Bot)
*Objective: Create specialized Views or materialized tables in MariaDB that calculate the stats required for comparisons, reasoning, and predictions.*

1. **Player Aggregated Stats (Views):**
   - Batting stats: Total runs, highest score, average, strike rate, 50s, 100s.
   - Bowling stats: Total wickets, economy rate, average, best bowling figures, 5-wicket hauls.
2. **Recent Form & Trend Analysis:**
   - Calculate rolling averages (e.g., "Performance in the last 5 matches"). This is crucial for the **Prediction** aspect.
3. **Head-to-Head & Comparative Metrics:**
   - Create tables/views that make it easy to extract how Player A compares to Player B, or how a Batsman performs against a specific Bowling Style.

## Phase 4: Dataset Generation Strategy (Prompt-Response Design)
*Objective: Build the "high-class" JSONL dataset using diverse, rich, and formatted structures.*

1. **Fact Retrieval / Informational Prompts:**
   - Prompt: "Who is [Player]?" / "Tell me about [Player]."
   - Response: Rich paragraph format, replacing IDs with names.
2. **Comparative Analysis Prompts:**
   - Prompt: "Compare [Player A] and [Player B]."
   - Response: Markdown tables showing side-by-side aggregated stats (from Phase 3) and reasoned text highlighting who is better at what.
3. **Reasoning & Visual/Table Prompts:**
   - Prompt: "Give me the career summary of [Player] in a table format."
   - Response: Beautifully formatted Markdown tables.
4. **Prediction & Form Prompts:**
   - Prompt: "Based on recent form, how is [Player] expected to perform?"
   - Response: Reasoned prediction using the "Recent Form" views created in Phase 3. "Based on a strike rate of 145 over the last 5 matches..."

## Phase 5: LLM Fine-Tuning Pipeline
*Objective: Train the model effectively without overfitting (memorizing) or underfitting (failing to learn).*

1. **Prompt Variety & Augmentation:**
   - Ensure for every data point, there are 5-10 different ways the user might ask the question.
2. **Train / Validation / Test Split:**
   - Split the generated dataset (e.g., 80% train, 10% validation, 10% test).
3. **Hyperparameter Tuning Strategy:**
   - Plan for adjusting learning rates, batch sizes, and epochs based on validation loss to prevent overfitting.
4. **Evaluation Criteria:**
   - Define how we will test the model post-training (e.g., asking it about a player it hasn't seen in the training set to test if it learned the *structure* of answering, not just memorized the text).

---
*Note: We will proceed through these phases step-by-step, starting with Phase 1, upon your approval.*
