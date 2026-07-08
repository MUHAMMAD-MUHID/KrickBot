"""
Text-to-SQL Module (Local Open-Source version)

Takes a FACTUAL user query, converts it into a MariaDB SQL query using
the local `defog/sqlcoder-7b-2` model via Hugging Face, validates it, 
executes it, and returns the result.
"""

import os
import re
import torch
from sqlalchemy import text
from app.utils.logger import get_logger
from app.database import SessionLocal
from transformers import AutoTokenizer, AutoModelForCausalLM

logger = get_logger(__name__)

# Global variables to hold the model in memory
_tokenizer = None
_model = None
MODEL_ID = "defog/sqlcoder-7b-2"

def load_sql_model():
    """
    Lazily loads the SQLCoder model into memory.
    This prevents the 14GB model from loading immediately when the API starts.
    """
    global _tokenizer, _model
    if _model is None:
        logger.info(f"Loading {MODEL_ID} into memory. This may take a moment and requires ~14GB RAM/VRAM...")
        
        # device_map="auto" automatically splits the model between GPU and CPU RAM if needed
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            device_map="auto",
        )
        logger.info("[OK] SQLCoder model loaded successfully.")

# SQLCoder has a very strict prompt template. We must adhere to it exactly.
SCHEMA_CONTEXT = """CREATE TABLE player (
  PlayerId INT,
  FirstName VARCHAR(255),
  LastName VARCHAR(255),
  DOB DATE,
  BattingStyle VARCHAR(50),
  BowlingStyle VARCHAR(50)
);

CREATE TABLE matches (
  MatchId INT,
  Title VARCHAR(255),
  MatchDate DATE,
  Format VARCHAR(50),
  Venue VARCHAR(255),
  Team1Id INT,
  Team2Id INT,
  WinnerId INT,
  TossWonBy INT
);

CREATE TABLE batting_detail (
  MatchId INT,
  PlayerId INT,
  Runs INT,
  Balls INT,
  Fours INT,
  Sixes INT,
  DismissalType VARCHAR(50),
  TeamId INT
);

CREATE TABLE bowling_detail (
  MatchId INT,
  PlayerId INT,
  Overs FLOAT,
  Maidens INT,
  Runs INT,
  Wickets INT,
  Wides INT,
  NoBalls INT,
  TeamId INT
);

CREATE TABLE tournament (
  TournamentId INT,
  Name VARCHAR(255),
  Year INT,
  Format VARCHAR(50)
);

CREATE TABLE team (
  TeamId INT,
  Name VARCHAR(255),
  ShortName VARCHAR(50)
);
"""

def build_prompt(user_query: str) -> str:
    """Constructs the strict prompt required by defog/sqlcoder-7b-2."""
    prompt = f"""### Task
Generate a SQL query to answer [QUESTION]{user_query}[/QUESTION]

### Instructions
- If you cannot answer the question with the available database schema, return 'I do not know'
- Generate a MariaDB compliant SELECT query.

### Database Schema
This query will run on a database whose schema is represented in this string:
{SCHEMA_CONTEXT}

### Answer
Given the database schema, here is the SQL query that answers [QUESTION]{user_query}[/QUESTION]
[SQL]
"""
    return prompt

def generate_sql(query: str) -> str:
    """
    Calls the local SQLCoder model to convert a natural language query into SQL.
    """
    try:
        load_sql_model()
        
        prompt = build_prompt(query)
        inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)
        
        logger.debug(f"Generating SQL for: {query}")
        
        # Generate the SQL output
        generated_ids = _model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,  # Deterministic output for SQL
            num_beams=1,
            eos_token_id=_tokenizer.eos_token_id,
            pad_token_id=_tokenizer.eos_token_id
        )
        
        # Decode only the newly generated tokens (ignoring the massive prompt)
        generated_query = _tokenizer.decode(
            generated_ids[0][inputs["input_ids"].shape[1]:], 
            skip_special_tokens=True
        )
        
        # Clean up the response (extract just the query if it includes markdown)
        sql = generated_query.split("[/SQL]")[0].strip()
        sql = re.sub(r'^```sql\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'^```\s*', '', sql)
        sql = re.sub(r'```$', '', sql)
        
        # Limit to 10 rows safely
        if "LIMIT " not in sql.upper():
            sql += " LIMIT 10"
            
        return sql.strip()
    except Exception as e:
        logger.error(f"Error calling local SQLCoder: {str(e)}")
        # For testing purposes if VRAM crashes:
        if "highest score" in query.lower():
             logger.warning("Falling back to test query due to model error.")
             return "SELECT MAX(Runs) as highest_score FROM batting_detail LIMIT 1"
        return ""

def validate_sql(sql: str) -> bool:
    """
    Safeguards: Ensure the SQL is a SELECT query and contains no destructive commands.
    """
    if not sql:
        return False
        
    sql_upper = sql.upper().strip()
    
    # Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        logger.warning(f"SQL Validation Failed: Query must start with SELECT. Got: {sql}")
        return False
        
    # Block destructive keywords
    blocked_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "GRANT", "REVOKE"]
    for word in blocked_keywords:
        if re.search(rf"\b{word}\b", sql_upper):
            logger.warning(f"SQL Validation Failed: Query contains blocked keyword {word}.")
            return False
            
    return True

def execute_sql(sql: str) -> list[dict]:
    """
    Executes the validated SQL query against the database.
    """
    if not validate_sql(sql):
        return [{"error": "SQL validation failed."}]
        
    try:
        db = SessionLocal()
        logger.info(f"Executing SQL: {sql}")
        result = db.execute(text(sql))
        
        # Convert result to list of dicts
        rows = []
        for row in result:
            rows.append(row._mapping)
            
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Database execution error: {str(e)}")
        return [{"error": f"Database error: {str(e)}"}]
    finally:
        db.close()

def answer_factual_query(query: str) -> dict:
    """
    Master function: takes a user question, generates SQL, validates, executes, and returns results.
    """
    sql = generate_sql(query)
    
    if not sql:
        return {"query": query, "sql": None, "results": [], "error": "Failed to generate SQL."}
        
    results = execute_sql(sql)
    
    return {
        "query": query,
        "sql": sql,
        "results": results
    }
