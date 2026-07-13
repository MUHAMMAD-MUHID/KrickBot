"""
Generates a JSONL dataset for LLM fine-tuning from the MariaDB database.
Format: Alpaca/Instruct (instruction, input, output).
"""

import sys
import os
import json
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from app.utils.logger import get_logger

logger = get_logger(__name__)

def generate_player_dataset(conn) -> list:
    dataset = []
    # Fetch top 100 players to keep dataset manageable
    res = conn.execute(text("SELECT * FROM player LIMIT 100"))
    for row in res:
        full_name = row.FullName
        if not full_name:
            continue
            
        # Example 1: Bio
        instruction = f"Tell me about the cricket player {full_name}."
        output_parts = [f"{full_name} is a cricket player."]
        if row.DOB and str(row.DOB) != "0000-00-00":
            output_parts.append(f"They were born on {row.DOB}.")
        if row.MajorTeams:
            output_parts.append(f"They have played for major teams including {row.MajorTeams}.")
        if row.PlayingRole:
            output_parts.append(f"Their primary playing role is {row.PlayingRole}.")
            
        dataset.append({
            "instruction": instruction,
            "input": "",
            "output": " ".join(output_parts)
        })
        
        # Example 2: Playing style
        if row.BattingStyle or row.BowlingStyle:
            instruction_style = f"What is the playing style of {full_name}?"
            style_parts = []
            if row.BattingStyle:
                style_parts.append(f"batting style is {row.BattingStyle}")
            if row.BowlingStyle:
                style_parts.append(f"bowling style is {row.BowlingStyle}")
            
            output_style = f"{full_name}'s " + " and ".join(style_parts) + "."
            dataset.append({
                "instruction": instruction_style,
                "input": "",
                "output": output_style
            })
            
    return dataset

def generate_match_dataset(conn) -> list:
    dataset = []
    # Fetch 100 matches
    res = conn.execute(text("SELECT * FROM matches LIMIT 100"))
    for row in res:
        if not row.Team1Name or not row.Team2Name:
            continue
            
        instruction = f"Provide a summary of the match between {row.Team1Name} and {row.Team2Name} on {row.Dated}."
        
        output = f"This was a {row.Format} match. "
        if row.Toss:
            output += f"The toss was won by Team ID {row.Toss}. "
        if row.WinnerName:
            output += f"The match was won by {row.WinnerName}. "
        if row.ResultDetail:
            output += f"Result details: {row.ResultDetail}."
            
        dataset.append({
            "instruction": instruction.strip(),
            "input": "",
            "output": output.strip()
        })
    return dataset

def main():
    output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dataset.jsonl")
    
    logger.info("Connecting to database to generate fine-tuning dataset...")
    all_data = []
    
    try:
        with engine.connect() as conn:
            players = generate_player_dataset(conn)
            matches = generate_match_dataset(conn)
            
            all_data.extend(players)
            all_data.extend(matches)
            
        logger.info(f"Generated {len(all_data)} instruction-response pairs.")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in all_data:
                f.write(json.dumps(item) + "\n")
                
        logger.info(f"Dataset successfully saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Failed to generate dataset: {e}")

if __name__ == "__main__":
    main()
