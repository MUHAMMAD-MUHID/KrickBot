import os
import json
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

# Load database credentials from .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "krickbot")

OUTPUT_FILE = "../dataset.jsonl"

# Define the tables you want to extract data from. 
# We ignore purely relational mapping tables or metadata tables to keep the dataset clean.
TARGET_TABLES = [
    "player",
    "article",
    "matches",
    "team",
    "news",
    "tournament",
    "ground",
    "batting_stats",
    "bowling_stats"
]

def format_row_to_text(table_name, row):
    """
    Dynamically converts a database row (dictionary) into a natural language response.
    """
    # Remove null or empty values to keep the text clean
    clean_row = {k: v for k, v in row.items() if v is not None and str(v).strip() != ""}
    
    if not clean_row:
        return None

    # Try to find a 'Name' or 'Title' column to use as the main subject of the prompt
    subject_keys = ['Name', 'Title', 'Heading', 'PlayerName', 'TeamName', 'FullName']
    subject = f"Record ID {list(clean_row.values())[0]}" # Fallback
    
    for key in subject_keys:
        if key in clean_row:
            subject = str(clean_row[key])
            break

    # Generate Prompt
    prompt = f"Provide details about the {table_name}: {subject}"
    
    # Generate Response
    response_parts = [f"Here are the details for the {table_name} '{subject}':"]
    for col, val in clean_row.items():
        # Clean up column names for readability (e.g. DOB -> D O B, PlayerId -> Player Id)
        readable_col = ''.join([' ' + c if c.isupper() else c for c in col]).strip()
        response_parts.append(f"- {readable_col}: {val}")
        
    response = "\n".join(response_parts)
    
    return prompt, response

def main():
    print(f"Connecting to database '{DB_NAME}' at {DB_HOST}...")
    
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            cursorclass=DictCursor
        )
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    training_examples = []
    total_records = 0

    with connection:
        with connection.cursor() as cursor:
            # 1. Get all tables in the database
            cursor.execute("SHOW TABLES")
            all_tables = [list(row.values())[0] for row in cursor.fetchall()]
            
            for table in TARGET_TABLES:
                if table not in all_tables:
                    print(f"Warning: Table '{table}' not found in database. Skipping.")
                    continue
                
                print(f"Extracting data from '{table}'...")
                
                # Fetch all rows from the table
                # NOTE: If a table is massive (>100k rows), you might want to add a LIMIT here
                cursor.execute(f"SELECT * FROM `{table}` LIMIT 10000") 
                rows = cursor.fetchall()
                
                for row in rows:
                    result = format_row_to_text(table, row)
                    if result:
                        prompt, response = result
                        training_examples.append({
                            "messages": [
                                {"role": "user", "content": prompt},
                                {"role": "model", "content": response}
                            ]
                        })
                        total_records += 1

    # 2. Save to JSONL
    print(f"\nExtracted {total_records} valid records.")
    print(f"Saving to {OUTPUT_FILE}...")
    
    # Ensure directory exists if saving elsewhere, here we save to parent dir (workspace root)
    output_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for example in training_examples:
            f.write(json.dumps(example) + '\n')
            
    print(f"Successfully generated fine-tuning dataset at {os.path.abspath(output_path)}")
    print("You can now upload this dataset to Google Colab and run your finetuning pipeline!")

if __name__ == "__main__":
    main()
