"""
Document Generator — converts database rows into natural-language documents.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class Document:
    """A processed document ready for embedding and upsertion."""
    doc_id: str
    content: str
    metadata: Dict[str, Any]

def clean_text(text: Optional[str]) -> str:
    """Helper to clean string fields."""
    if not text:
        return ""
    return str(text).strip()

def generate_player_document(row: Dict[str, Any]) -> Optional[Document]:
    player_id = row.get("PlayerId")
    if not player_id:
        return None
        
    full_name = clean_text(row.get("FullName"))
    dob = row.get("DOB")
    major_teams = clean_text(row.get("MajorTeams"))
    batting_style = clean_text(row.get("BattingStyle"))
    bowling_style = clean_text(row.get("BowlingStyle"))
    playing_role = clean_text(row.get("PlayingRole"))
    
    content_parts = [f"Player {full_name} is a cricket player."]
    if dob and str(dob) != "0000-00-00":
        content_parts.append(f"Date of birth: {dob}.")
    if major_teams:
        content_parts.append(f"Major teams: {major_teams}.")
    if batting_style:
        content_parts.append(f"Batting style: {batting_style}.")
    if bowling_style:
        content_parts.append(f"Bowling style: {bowling_style}.")
    if playing_role:
        content_parts.append(f"Playing role: {playing_role}.")
        
    return Document(
        doc_id=f"player::{player_id}",
        content=" ".join(content_parts),
        metadata={"type": "player", "player_id": player_id}
    )

def generate_match_document(row: Dict[str, Any]) -> Optional[Document]:
    match_no = row.get("MatchNo")
    if not match_no:
        return None
        
    format_type = clean_text(row.get("Format"))
    team1 = clean_text(row.get("Team1Name"))
    team2 = clean_text(row.get("Team2Name"))
    winner = clean_text(row.get("WinnerName"))
    result = clean_text(row.get("ResultDetail"))
    dated = row.get("Dated")
    toss = clean_text(row.get("TossName"))
    
    content = f"Match {match_no}."
    if format_type:
        content += f" Format: {format_type}."
    if team1 and team2:
        content += f" {team1} played against {team2}."
    if dated:
        content += f" Date: {dated}."
    if toss:
        content += f" Toss won by {toss}."
    if winner:
        content += f" Winner: {winner}."
    if result:
        content += f" Result: {result}."
        
    return Document(
        doc_id=f"match::{match_no}",
        content=content.strip(),
        metadata={"type": "match", "match_no": match_no}
    )

def generate_batting_performance_document(row: Dict[str, Any]) -> Optional[Document]:
    match_no = row.get("MatchNo")
    innings = row.get("Innings")
    player_id = row.get("PlayerId")
    if not all([match_no, innings, player_id]):
        return None
        
    batsman = clean_text(row.get("BatsmanName")) or f"Player {player_id}"
    runs = row.get("Runs") or 0
    balls = row.get("BallsFaced") or 0
    fours = row.get("Fours") or 0
    sixes = row.get("Sixes") or 0
    how_out = clean_text(row.get("HowOut"))
    
    content = f"In match {match_no}, innings {innings}, batsman {batsman} scored {runs} runs off {balls} balls."
    if fours or sixes:
        content += f" They hit {fours} fours and {sixes} sixes."
    if how_out and how_out.lower() != "not out":
        content += f" Dismissal: {how_out}."
    else:
        content += " They were not out."
        
    return Document(
        doc_id=f"batting_perf::{match_no}_{innings}_{player_id}",
        content=content,
        metadata={
            "type": "batting_performance", 
            "match_no": match_no,
            "innings": innings,
            "player_id": player_id
        }
    )

def generate_bowling_performance_document(row: Dict[str, Any]) -> Optional[Document]:
    match_no = row.get("MatchNo")
    innings = row.get("Innings")
    player_id = row.get("PlayerId")
    if not all([match_no, innings, player_id]):
        return None
        
    bowler = clean_text(row.get("BowlerName")) or f"Player {player_id}"
    overs = row.get("Overs") or 0
    maidens = row.get("Maiden") or 0
    runs = row.get("Runs") or 0
    wickets = row.get("Wickets") or 0
    
    content = f"In match {match_no}, innings {innings}, bowler {bowler} bowled {overs} overs. They gave {runs} runs and took {wickets} wickets."
    if maidens:
        content += f" They bowled {maidens} maiden overs."
        
    return Document(
        doc_id=f"bowling_perf::{match_no}_{innings}_{player_id}",
        content=content,
        metadata={
            "type": "bowling_performance", 
            "match_no": match_no,
            "innings": innings,
            "player_id": player_id
        }
    )

def generate_team_document(row: Dict[str, Any]) -> Optional[Document]:
    team_id = row.get("TeamId")
    if not team_id:
        return None
    team_name = clean_text(row.get("TeamName"))
    level = clean_text(row.get("Level"))
    content = f"Team {team_name}."
    if level:
        content += f" Playing level: {level}."
    return Document(
        doc_id=f"team::{team_id}",
        content=content,
        metadata={"type": "team", "team_id": team_id}
    )

def generate_tournament_document(row: Dict[str, Any]) -> Optional[Document]:
    tournament_id = row.get("TournamentId")
    if not tournament_id:
        return None
    name = clean_text(row.get("Name"))
    fmt = clean_text(row.get("Format"))
    detail = clean_text(row.get("Detail"))
    
    content = f"Tournament {name}."
    if fmt:
        content += f" Format: {fmt}."
    if detail:
        content += f" Details: {detail}."
    return Document(
        doc_id=f"tournament::{tournament_id}",
        content=content,
        metadata={"type": "tournament", "tournament_id": tournament_id}
    )

# Map table names to their generator functions
GENERATORS = {
    "player": generate_player_document,
    "matches": generate_match_document,
    "batting_detail": generate_batting_performance_document,
    "bowling_detail": generate_bowling_performance_document,
    "team": generate_team_document,
    "tournament": generate_tournament_document
}

def generate_documents_from_rows(table_name: str, rows: List[Dict[str, Any]]) -> List[Document]:
    """
    Takes a list of raw database rows and converts them to structured Documents.
    Returns a list of generated Document objects.
    """
    if table_name not in GENERATORS:
        logger.warning(f"No document generator configured for table: {table_name}")
        return []
        
    generator_fn = GENERATORS[table_name]
    documents = []
    
    for row in rows:
        try:
            doc = generator_fn(row)
            if doc:
                documents.append(doc)
        except Exception as e:
            logger.error(f"Error generating document for {table_name} row: {e}")
            
    logger.info(f"Generated {len(documents)} documents for {table_name}")
    return documents
