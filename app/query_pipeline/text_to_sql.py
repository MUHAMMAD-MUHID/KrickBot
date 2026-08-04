"""
Text-to-SQL Module (Groq version)

Takes a FACTUAL user query, converts it into a MariaDB SQL query using
Groq, validates it, executes it, and returns the result.
"""

import os
import re
from sqlalchemy import text
from app.utils.logger import get_logger
from app.database import SessionLocal
from app.config import settings
from groq import Groq

logger = get_logger(__name__)

# ─── Focused Schema: Only cricket-relevant tables with ALL columns ───
# This gives the LLM full visibility into column names, types, and relationships.
SCHEMA_CONTEXT = """
-- ======================== CORE MATCH TABLES ========================

CREATE TABLE matches (
  MatchNo int PRIMARY KEY,          -- Unique match identifier
  Season varchar(7),                -- e.g. '2019', '2020' (VARCHAR, not a date!)
  Dated datetime,                   -- Match date
  Winner int,                       -- FK → team.TeamId (winning team)
  RunnerUP int,                     -- FK → team.TeamId
  WinnerName varchar(45),           -- Denormalized winner team name
  RunnerupName varchar(45),         -- Denormalized runner-up team name
  Team1 int NOT NULL,               -- FK → team.TeamId
  Team2 int NOT NULL,               -- FK → team.TeamId
  Team1Name varchar(45),            -- Denormalized team 1 name
  Team2Name varchar(45),            -- Denormalized team 2 name
  ResultDetail varchar(150),        -- e.g. 'Won by 5 wickets'
  ResultType enum('WinLoss','Tie','Draw','No Result','Abandoned','Awarded','Conceded'),
  Overs int,                        -- Match overs limit
  Format varchar(20),               -- e.g. 'One Day', 'T20', 'Test'
  Type varchar(20),                 -- e.g. 'Friendly Match', 'League'
  TournamentId int,                 -- FK → tournament.TournamentId
  GroundId int,                     -- FK → ground.GroundId
  ManOfMatch int,                   -- FK → player.PlayerId
  Toss int,                         -- FK → team.TeamId (who won toss)
  Status varchar(1),                -- 'S' = scheduled, 'C' = completed
  Summary varchar(3500),
  CityName varchar(50),
  CountryName varchar(50)
);

CREATE TABLE innings (
  MatchNo int NOT NULL,             -- FK → matches.MatchNo
  Innings int NOT NULL,             -- 1 or 2
  Score int,                        -- Total runs scored
  Overs double,                     -- Overs bowled
  Wickets int DEFAULT 0,            -- Wickets fallen
  BattingTeam int,                  -- FK → team.TeamId
  BowlingTeam int,                  -- FK → team.TeamId
  BattingTeamName varchar(50),
  BowlingTeamName varchar(50),
  PRIMARY KEY (MatchNo, Innings)
);

CREATE TABLE fow (
  MatchNo int NOT NULL,             -- FK → matches.MatchNo
  Innings int NOT NULL,
  Wicket int NOT NULL,              -- Wicket number (1-10)
  Overs double,
  Score int,                        -- Score at fall of wicket
  Batsman int,                      -- FK → player.PlayerId
  Bowler int,                       -- FK → player.PlayerId
  BatsmanName varchar(50),
  BowlerName varchar(50),
  HowOut varchar(10),
  PRIMARY KEY (MatchNo, Innings, Wicket)
);

-- ======================== PLAYER & TEAM ========================

CREATE TABLE team (
  TeamId int PRIMARY KEY AUTO_INCREMENT,
  TeamName varchar(50),
  ShortName varchar(10),
  Level varchar(30),
  Season varchar(7),
  Coach varchar(30),
  Captain int                       -- FK → player.PlayerId
);

CREATE TABLE player (
  PlayerId int PRIMARY KEY AUTO_INCREMENT,
  FullName varchar(100),
  DOB date,
  BattingStyle varchar(50),
  BowlingStyle varchar(50),
  PlayingRole varchar(30),          -- e.g. 'Batsman', 'Bowler', 'All-Rounder'
  ClubId int,                       -- FK → club.ClubId
  ShortName varchar(10)
);

CREATE TABLE club (
  ClubId int PRIMARY KEY AUTO_INCREMENT,
  ClubName varchar(45),
  AssociationId int
);

-- ======================== MATCH-LEVEL DETAIL ========================

CREATE TABLE batting_detail (
  MatchNo int NOT NULL,             -- FK → matches.MatchNo
  Innings int NOT NULL,
  PlayerId int NOT NULL,            -- FK → player.PlayerId
  Runs int DEFAULT 0,
  BallsFaced int DEFAULT 0,
  Fours int DEFAULT 0,
  Sixes int DEFAULT 0,
  Singles int DEFAULT 0,
  Doubles int DEFAULT 0,
  Threes int DEFAULT 0,
  Dots int DEFAULT 0,
  NotOut tinyint,                   -- 1 = not out, 0 = out
  HowOut varchar(20),               -- e.g. 'Bowled', 'Caught', 'LBW'
  Bowler int,                       -- FK → player.PlayerId (bowler who got the wicket)
  Fielder int,                      -- FK → player.PlayerId
  BatsmanName varchar(100),
  TeamId int,                       -- FK → team.TeamId
  TeamName varchar(100),
  Position int DEFAULT 0,           -- Batting position
  PRIMARY KEY (MatchNo, Innings, PlayerId)
);

CREATE TABLE bowling_detail (
  MatchNo int NOT NULL,             -- FK → matches.MatchNo
  Innings int NOT NULL,
  PlayerId int NOT NULL,            -- FK → player.PlayerId
  Overs double DEFAULT 0,
  Maiden int DEFAULT 0,
  Runs int DEFAULT 0,
  Wickets int DEFAULT 0,
  Wides int DEFAULT 0,
  NoBalls int DEFAULT 0,
  BowlerName varchar(100),
  TeamId int,                       -- FK → team.TeamId
  TeamName varchar(45),
  Balls int,
  PRIMARY KEY (MatchNo, Innings, PlayerId)
);

-- ======================== AGGREGATED STATS ========================

CREATE TABLE batting_stats (
  PlayerId int NOT NULL,            -- FK → player.PlayerId
  Season varchar(10) NOT NULL,      -- e.g. '2019'
  Stage varchar(20) NOT NULL,
  Format varchar(10) NOT NULL,      -- e.g. 'T20', 'ODI'
  ICC varchar(20),                  -- '1' = ICC-recognised stats, '0' = non-ICC
  Matches int DEFAULT 0,
  Inn int DEFAULT 0,
  NotOut int DEFAULT 0,
  Runs int DEFAULT 0,
  HS int DEFAULT 0,                 -- Highest Score
  Average decimal(6,2),
  BF int DEFAULT 0,                 -- Balls Faced
  SR decimal(6,2),                  -- Strike Rate
  Hundreds int DEFAULT 0,
  Fifties int DEFAULT 0,
  Zeros int DEFAULT 0,              -- Ducks
  Fours int DEFAULT 0,
  Sixes int DEFAULT 0,
  Catches int,
  Stumps int,
  PlayerName varchar(50),
  PRIMARY KEY (PlayerId, Season, Stage, Format)
);

CREATE TABLE bowling_stats (
  PlayerId int NOT NULL,            -- FK → player.PlayerId
  Season varchar(10) NOT NULL,
  Stage varchar(20) NOT NULL,
  Format varchar(10) NOT NULL,
  ICC varchar(20),                  -- '1' = ICC-recognised stats, '0' = non-ICC
  Matches int DEFAULT 0,
  Inn int DEFAULT 0,
  Balls int DEFAULT 0,
  Runs int DEFAULT 0,
  Wickets int DEFAULT 0,
  BBI varchar(8),                   -- Best Bowling in Innings
  Average decimal(6,2),
  Economy decimal(6,2),
  StrikeRate decimal(6,2),
  Fourfor int DEFAULT 0,            -- 4-wicket hauls
  Fivefor int DEFAULT 0,            -- 5-wicket hauls
  PlayerName varchar(50),
  PRIMARY KEY (PlayerId, Season, Stage, Format)
);

-- ======================== TOURNAMENT & GROUND ========================

CREATE TABLE tournament (
  TournamentId int PRIMARY KEY AUTO_INCREMENT,
  Name varchar(80),
  Format varchar(45),
  Season varchar(10),
  StartDate datetime,
  EndDate datetime,
  Winner int,                       -- FK → team.TeamId
  RunnerUp int,                     -- FK → team.TeamId
  Level varchar(10),
  Status char(1)                    -- 'A' = active, etc.
);

CREATE TABLE ground (
  GroundId int PRIMARY KEY AUTO_INCREMENT,
  GroundName varchar(50),
  Address varchar(100),
  CityId int,                       -- FK → city.CityId
  CountryCode int                   -- FK → country.CountryCode
);

CREATE TABLE city (
  CityId int PRIMARY KEY AUTO_INCREMENT,
  CityName varchar(50),
  CountryCode int                   -- FK → country.CountryCode
);

CREATE TABLE country (
  CountryCode int PRIMARY KEY,
  CountryName varchar(50),
  BoardName varchar(60),
  ISOCode2 varchar(2),
  ISOCode3 varchar(3)
);

CREATE TABLE ball_by_ball (
  BallId int PRIMARY KEY AUTO_INCREMENT,
  MatchNo int,                      -- FK → matches.MatchNo
  Innings int,
  Over int,
  Ball int,
  BatsmanId int,                    -- FK → player.PlayerId
  BowlerId int,                    -- FK → player.PlayerId
  Runs int DEFAULT 0,
  Wide int DEFAULT 0,
  NoBall int DEFAULT 0,
  Wicket int DEFAULT 0,
  BatsmanName varchar(100),
  BowlerName varchar(100)
);
"""

# ─── Key notes for the LLM to understand data patterns ───
SCHEMA_NOTES = """
### Important Notes:
- The `Season` column is a VARCHAR like '2019', '2020'. Do NOT use YEAR(Dated) to filter by year; use `Season = '2019'` or `WHERE matches.Season = '2019'`.
- CRITICAL: `batting_detail` and `bowling_detail` DO NOT have a `Season` column. For queries filtering by Season or year (e.g. "in 2024"), use `batting_stats` / `bowling_stats`, OR JOIN `matches` ON `batting_detail.MatchNo = matches.MatchNo`.
- `matches.Winner` is a TeamId (int FK). `matches.WinnerName` is the denormalized team name (varchar). Use WinnerName for display.
- `matches.Team1Name` and `matches.Team2Name` are denormalized team names. You usually don't need to JOIN team table.
- `batting_detail.BatsmanName` and `bowling_detail.BowlerName` are denormalized. You usually don't need to JOIN player table.
- For "who won the most matches", COUNT matches grouped by WinnerName.
- For "highest scorer", use batting_detail or batting_stats.
- For "best bowler", use bowling_detail (match-level) or bowling_stats (aggregated).
- `batting_stats` and `bowling_stats` are pre-aggregated per player per season. Use these for season-level stats.
- For "ICC", "international", or "ICC-recognised" stats, filter batting_stats/bowling_stats with `ICC = '1'`.
- For maiden-over questions, use `bowling_detail` because `bowling_stats` does not have a Maiden column.
- For stadium/ground location questions, use `ground` joined to `city` and `country`.
- CRITICAL: NEVER use UNION between batting_stats and bowling_stats — they have different column counts and UNION will always fail. Pick ONE table based on the question.
- CRITICAL: NEVER JOIN batting_stats with bowling_stats — they share column names (PlayerName, Runs, Season) causing ambiguity errors. Query them separately.
- If the user asks about a player's "stats" or "achievements" without specifying batting or bowling, query batting_stats ONLY (batting is the default).
- If the user asks specifically about bowling/wickets, query bowling_stats ONLY.
- Use LIKE '%name%' for player name searches since names may not match exactly. Correct obvious misspellings of famous players (e.g. 'baber azam' -> 'Babar Azam') before putting them in the LIKE clause.

### Example Queries:
Q: "Who won the most matches in 2019?"
SQL: SELECT WinnerName, COUNT(*) AS wins FROM matches WHERE Season = '2019' AND Winner IS NOT NULL GROUP BY WinnerName ORDER BY wins DESC LIMIT 10

Q: "Who scored the highest runs in a single match?"
SQL: SELECT BatsmanName, Runs, MatchNo FROM batting_detail ORDER BY Runs DESC LIMIT 1

Q: "Top 5 bowlers by wickets in 2020"
SQL: SELECT PlayerName, SUM(Wickets) AS total_wickets FROM bowling_stats WHERE Season = '2020' GROUP BY PlayerName ORDER BY total_wickets DESC LIMIT 5

Q: "Top 5 players with most maiden overs"
SQL: SELECT BowlerName, SUM(Maiden) AS total_maidens, COUNT(DISTINCT MatchNo) AS matches FROM bowling_detail WHERE Maiden > 0 GROUP BY BowlerName ORDER BY total_maidens DESC LIMIT 5

Q: "Which player has more runs in ICC?"
SQL: SELECT PlayerName, SUM(Runs) AS total_runs, SUM(Matches) AS matches FROM batting_stats WHERE ICC = '1' GROUP BY PlayerName ORDER BY total_runs DESC LIMIT 10

Q: "Pakistan has stadium in which cities?"
SQL: SELECT c.CityName, COUNT(*) AS stadiums FROM ground g LEFT JOIN city c ON g.CityId = c.CityId LEFT JOIN country co ON COALESCE(g.CountryCode, c.CountryCode) = co.CountryCode WHERE co.CountryName LIKE '%Pakistan%' GROUP BY c.CityName ORDER BY stadiums DESC LIMIT 20

Q: "Which country has how many stadiums?"
SQL: SELECT co.CountryName, COUNT(*) AS stadiums FROM ground g LEFT JOIN country co ON g.CountryCode = co.CountryCode GROUP BY co.CountryName ORDER BY stadiums DESC LIMIT 20

Q: "How many matches were played in 2019?"
SQL: SELECT COUNT(*) AS total_matches FROM matches WHERE Season = '2019'

Q: "List match winners in 2019"
SQL: SELECT MatchNo, Dated, WinnerName, RunnerupName, ResultDetail FROM matches WHERE Season = '2019' AND Winner IS NOT NULL ORDER BY Dated

Q: "Tell me achievements of Shoaib Malik" or "Shoaib Malik stats"
SQL: SELECT PlayerName, Season, Matches, Runs, HS, Average, SR, Hundreds, Fifties FROM batting_stats WHERE PlayerName LIKE '%Shoaib Malik%'

Q: "Shoaib Malik bowling stats" or "how many wickets did Shoaib Malik take"
SQL: SELECT PlayerName, Season, Matches, Wickets, Average, Economy, BBI FROM bowling_stats WHERE PlayerName LIKE '%Shoaib Malik%'
"""


def build_prompt(user_query: str) -> str:
    """Constructs a rich prompt with schema, notes, and examples for accurate SQL generation."""
    prompt = f"""### Task
Generate a SQL query to answer [QUESTION]{user_query}[/QUESTION]

### Instructions
- If you cannot answer the question with the available database schema, return 'I do not know'
- Generate a MariaDB compliant SELECT query.
- Use the denormalized name columns (WinnerName, BatsmanName, etc.) when possible instead of JOINs.
- The Season column is a VARCHAR (e.g. '2019'). Never use YEAR() on it.
- Output ONLY the SQL query, nothing else.

### Database Schema
This query will run on a database whose schema is represented in this string:
{SCHEMA_CONTEXT}

{SCHEMA_NOTES}

### Answer
Given the database schema, here is the SQL query that answers [QUESTION]{user_query}[/QUESTION]
[SQL]
"""
    return prompt

def _sql_literal(value: str) -> str:
    """Escape a string for use in deterministic read-only SQL snippets."""
    return value.replace("'", "''")

def generate_known_sql(query: str) -> str:
    """
    Deterministic SQL for high-frequency leaderboard questions.

    This catches casual phrasing like "who has more runs in ICC" before the
    request goes to the LLM, which may otherwise treat "more" as a comparison
    between two named players.
    """
    lower_query = query.lower()

    asks_for_stadiums = re.search(r"\b(stadiums?|grounds?)\b", lower_query) is not None
    asks_for_cities = re.search(r"\b(cities|city)\b", lower_query) is not None
    asks_for_countries = re.search(r"\b(countries|country)\b", lower_query) is not None

    if asks_for_stadiums:
        known_countries = [
            "Pakistan", "India", "Sri Lanka", "Afghanistan", "Bangladesh",
            "Australia", "England", "New Zealand", "South Africa",
            "West Indies", "Zimbabwe", "Ireland", "Netherlands",
            "United Arab Emirates", "UAE", "Nepal", "Oman", "Scotland",
        ]
        country = next((name for name in known_countries if name.lower() in lower_query), None)
        country_filter = "United Arab Emirates" if country == "UAE" else country

        if asks_for_cities and country_filter:
            country_value = _sql_literal(country_filter)
            return (
                "SELECT c.CityName, COUNT(*) AS stadiums "
                "FROM ground g "
                "LEFT JOIN city c ON g.CityId = c.CityId "
                "LEFT JOIN country co ON COALESCE(g.CountryCode, c.CountryCode) = co.CountryCode "
                f"WHERE co.CountryName LIKE '%{country_value}%' "
                "GROUP BY c.CityName ORDER BY stadiums DESC LIMIT 50"
            )

        if asks_for_countries or not country_filter:
            return (
                "SELECT COALESCE(co.CountryName, 'Unknown') AS CountryName, COUNT(*) AS stadiums "
                "FROM ground g "
                "LEFT JOIN country co ON g.CountryCode = co.CountryCode "
                "GROUP BY COALESCE(co.CountryName, 'Unknown') "
                "ORDER BY stadiums DESC LIMIT 50"
            )

        country_value = _sql_literal(country_filter)
        return (
            "SELECT g.GroundName, c.CityName, co.CountryName "
            "FROM ground g "
            "LEFT JOIN city c ON g.CityId = c.CityId "
            "LEFT JOIN country co ON COALESCE(g.CountryCode, c.CountryCode) = co.CountryCode "
            f"WHERE co.CountryName LIKE '%{country_value}%' "
            "ORDER BY c.CityName, g.GroundName LIMIT 50"
        )

    leaderboard_words = ["most", "more", "highest", "top", "leading", "maximum"]

    asks_for_leaderboard = any(word in lower_query for word in leaderboard_words)
    asks_for_runs = re.search(r"\bruns?\b", lower_query) is not None
    asks_for_wickets = re.search(r"\bwickets?\b", lower_query) is not None
    asks_for_maidens = re.search(r"\bmaiden(?:s| overs?)?\b", lower_query) is not None

    if not asks_for_leaderboard or not (asks_for_runs or asks_for_wickets or asks_for_maidens):
        return ""

    limit_match = re.search(r"\btop\s+(\d{1,2})\b", lower_query)
    limit = min(int(limit_match.group(1)), 50) if limit_match else 10

    filters = []

    if re.search(r"\b(icc|international|icc[- ]?recognised|icc[- ]?recognized)\b", lower_query):
        filters.append("ICC = '1'")

    season_match = re.search(r"\b(19|20)\d{2}\b", lower_query)
    if season_match:
        filters.append(f"Season = '{season_match.group(0)}'")

    format_map = {
        "t20": "T20",
        "t20i": "T20",
        "odi": "ODI",
        "one day": "One Day",
        "test": "Test",
    }
    for phrase, db_format in format_map.items():
        if re.search(rf"\b{re.escape(phrase)}\b", lower_query):
            filters.append(f"Format = '{db_format}'")
            break

    where_clause = f" WHERE {' AND '.join(filters)}" if filters else ""

    if asks_for_maidens:
        detail_filters = ["Maiden > 0"]
        season_filter = next((item for item in filters if item.startswith("Season = ")), None)
        format_filter = next((item for item in filters if item.startswith("Format = ")), None)

        if season_filter or format_filter:
            match_filters = []
            if season_filter:
                match_filters.append(f"m.{season_filter}")
            if format_filter:
                match_filters.append(f"m.{format_filter}")
            return (
                "SELECT bd.BowlerName, SUM(bd.Maiden) AS total_maidens, "
                "COUNT(DISTINCT bd.MatchNo) AS matches "
                "FROM bowling_detail bd "
                "JOIN matches m ON bd.MatchNo = m.MatchNo "
                f"WHERE bd.Maiden > 0 AND {' AND '.join(match_filters)} "
                f"GROUP BY bd.BowlerName ORDER BY total_maidens DESC LIMIT {limit}"
            )

        return (
            "SELECT BowlerName, SUM(Maiden) AS total_maidens, "
            "COUNT(DISTINCT MatchNo) AS matches "
            "FROM bowling_detail "
            f"WHERE {' AND '.join(detail_filters)} "
            f"GROUP BY BowlerName ORDER BY total_maidens DESC LIMIT {limit}"
        )

    if asks_for_wickets and not asks_for_runs:
        return (
            "SELECT PlayerName, SUM(Wickets) AS total_wickets, SUM(Matches) AS matches "
            f"FROM bowling_stats{where_clause} "
            f"GROUP BY PlayerName ORDER BY total_wickets DESC LIMIT {limit}"
        )

    return (
        "SELECT PlayerName, SUM(Runs) AS total_runs, SUM(Matches) AS matches "
        f"FROM batting_stats{where_clause} "
        f"GROUP BY PlayerName ORDER BY total_runs DESC LIMIT {limit}"
    )

def generate_sql(query: str) -> str:
    """
    Calls Groq API to convert a natural language query into SQL.
    """
    try:
        logger.debug(f"Generating SQL for: {query}")

        known_sql = generate_known_sql(query)
        if known_sql:
            logger.info(f"Generated deterministic SQL: {known_sql}")
            return known_sql

        client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        if not client:
             logger.error("Groq API key not found. Cannot generate SQL.")
             return ""
             
        prompt = build_prompt(query)
        
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": (
                    "You are a SQL expert for a cricket database. "
                    "Output ONLY a valid MariaDB SELECT query. No explanations, no markdown fences, no comments. "
                    "Use the denormalized name columns (WinnerName, Team1Name, BatsmanName, PlayerName, etc.) for display. "
                    "The Season column is a VARCHAR like '2019', never use YEAR() on it. "
                    "If you cannot answer, output exactly: I do not know"
                )},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=512,
        )
        
        generated_query = completion.choices[0].message.content
        
        # If the model says it doesn't know, return empty
        if "i do not know" in generated_query.lower():
            logger.info("LLM responded: I do not know")
            return ""
        
        # Clean up the response (extract just the query if it includes markdown)
        sql = generated_query.split("[/SQL]")[0].strip()
        sql = re.sub(r'^```sql\s*', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'^```\s*', '', sql)
        sql = re.sub(r'```$', '', sql)
        sql = sql.strip()
        
        # Remove any leading text before SELECT
        select_idx = sql.upper().find("SELECT")
        if select_idx > 0:
            sql = sql[select_idx:]
        
        # Strip trailing semicolon so we can safely append LIMIT
        sql = sql.rstrip().rstrip(";")
        
        # Limit to 10 rows safely
        if "LIMIT " not in sql.upper():
            sql += " LIMIT 10"
            
        logger.info(f"Generated SQL: {sql}")
        return sql.strip()
    except Exception as e:
        logger.error(f"Error calling Groq for SQL: {str(e)}")
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
