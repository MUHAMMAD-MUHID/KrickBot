import os
import pymysql
import json
import random
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "krickbot")

OUTPUT_FILE = "refined_dataset.jsonl"
SYSTEM_PROMPT = "You are KrickBot, an analytical cricket assistant. Answer the user's question using ONLY the provided facts. Write naturally and avoid robotic repetition."

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        cursorclass=pymysql.cursors.DictCursor
    )

def clean_val(v, default="N/A"):
    if v is None or v == "" or str(v).lower() == "unknown":
        return default
    return str(v)

def format_message(question, facts, answer):
    # Fix Message Schema: Merge into single user turn with facts included
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"{question}\n\n{facts}"},
            {"role": "model", "content": answer}
        ]
    }

# Diverse templates for zero stats to avoid model learning robotic repetitions
ZERO_BATTING_TEMPLATES = [
    "{name} has yet to open their account for {team}, with 0 runs on the board.",
    "Despite being listed as a {role}, {name} hasn't scored any runs for {team} in recorded matches.",
    "Currently, {name} is sitting on zero runs with no batting average or strike rate to their name.",
    "There is no batting record of substance for {name} yet; they have 0 runs and an empty strike rate.",
    "As of the current facts, {name} (playing for {team}) has not troubled the scorers, managing 0 runs.",
    "Looking at the data, {name} hasn't managed to get off the mark yet. Their runs, average, and strike rate remain at zero.",
    "Unfortunately, {name} has blank stats across the board: 0 runs, 0 average, and 0 strike rate.",
    "{team}'s {name} has a completely barren batting record with zero runs so far."
]

ZERO_BOWLING_TEMPLATES = [
    "{name} has not picked up a single wicket for {team} in their {innings} innings of bowling.",
    "Despite bowling {innings} times, {name} is still searching for their first wicket.",
    "It's been a tough stint for {name} with the ball. Across {innings} innings, they remain wicketless.",
    "{team} has given {name} the ball in {innings} innings, but they have yet to strike.",
    "The wickets column remains empty for {name} after {innings} bowling innings.",
    "Looking at their bowling stats, {name} has failed to take any wickets in {innings} attempts.",
    "With {innings} innings under their belt, {name} is still waiting for their maiden wicket."
]

def generate_batting_profile(player, stats):
    name = clean_val(player.get('PlayerName'), 'The player')
    team = clean_val(player.get('ClubName'), 'an unspecified team')
    role = clean_val(player.get('PlayingRole'), 'player')
    
    innings = stats.get('TotalInnings', 0) or 0
    runs = stats.get('TotalRuns', 0) or 0
    avg = stats.get('BattingAverage', 0.0) or 0.0
    sr = stats.get('StrikeRate', 0.0) or 0.0
    
    questions = [
        f"Tell me about {name}'s batting.", f"Give me {name}'s batting stats.", 
        f"How has {name} performed with the bat?", f"What is {name}'s career batting record?"
    ]
    facts = f"[FACTS: Player: {name} | Team: {team} | Role: {role} | Innings: {innings} | Runs: {runs} | Avg: {avg:.2f} | SR: {sr:.2f}]"
    
    if runs == 0 and innings > 0:
        ans = random.choice(ZERO_BATTING_TEMPLATES).format(name=name, team=team, role=role)
    elif innings == 0:
        ans = random.choice([
            f"{name} hasn't actually batted in any recorded innings yet.",
            f"There are zero recorded innings for {name}, so they don't have a batting profile.",
            f"As a {role}, {name} is yet to face a ball in an official innings."
        ])
    elif innings <= 3:
        ans = random.choice([
            f"It's early days for {name}. In just {innings} innings, they've made {runs} runs (Avg: {avg:.2f}).",
            f"With only {innings} innings to their name, {name} has scored {runs} runs at a strike rate of {sr:.2f}.",
            f"{name} hasn't played much yet. Across {innings} innings, they've accumulated {runs} runs for {team}."
        ])
    else:
        ans = random.choice([
            f"{name} is an established {role} for {team}. Over {innings} innings, they have amassed {runs} runs at a solid average of {avg:.2f} and a strike rate of {sr:.2f}.",
            f"In {innings} innings, {name} has scored {runs} runs for {team}. Their career average sits at {avg:.2f}, while they strike the ball at {sr:.2f}.",
            f"Looking at {name}'s career, they've played {innings} innings and scored {runs} runs. They maintain a strike rate of {sr:.2f} (averaging {avg:.2f})."
        ])
        
    return format_message(random.choice(questions), facts, ans)

def generate_bowling_profile(player, stats):
    name = clean_val(player.get('PlayerName'), 'The player')
    team = clean_val(player.get('ClubName'), 'an unspecified team')
    innings = stats.get('TotalInningsBowled', 0) or 0
    wickets = stats.get('TotalWickets', 0) or 0
    econ = stats.get('EconomyRate', 0.0) or 0.0
    avg = stats.get('BowlingAverage', 0.0) or 0.0
    
    questions = [
        f"Summarize {name}'s career bowling stats.", f"How good is {name} as a bowler?",
        f"What is {name}'s bowling profile?"
    ]
    facts = f"[FACTS: Player: {name} | Team: {team} | Bowl Innings: {innings} | Wickets: {wickets} | Econ: {econ:.2f} | Avg: {avg:.2f}]"
    
    if innings == 0:
        ans = random.choice([
            f"According to the records, {name} has not bowled in any match yet.",
            f"There is no bowling data for {name} as they haven't bowled an official over."
        ])
    elif wickets == 0:
        ans = random.choice(ZERO_BOWLING_TEMPLATES).format(name=name, team=team, innings=innings)
    elif innings <= 3:
        ans = random.choice([
            f"With a limited record of only {innings} bowling innings, {name} has taken {wickets} wickets for {team}. Their early stats show an economy of {econ:.2f}.",
            f"Early on in their bowling career ({innings} innings), {name} has managed {wickets} wickets while going at {econ:.2f} runs per over."
        ])
    else:
        ans = random.choice([
            f"Across {innings} innings for {team}, {name} has proven to be a capable bowler, taking {wickets} wickets. They concede runs at an economy of {econ:.2f}.",
            f"Looking at {name}'s bowling profile, they have picked up {wickets} wickets in {innings} innings. Their bowling average is {avg:.2f} and their economy rate stands at {econ:.2f}."
        ])
        
    return format_message(random.choice(questions), facts, ans)

def generate_recent_form(player, stats, stat_type="batting"):
    name = clean_val(player.get('PlayerName'), 'The player')
    matches = stats.get('TotalMatches', 5) or 5
    
    if stat_type == "batting":
        runs = stats.get('TotalRuns', 0) or 0
        avg = stats.get('BattingAverage', 0.0) or 0.0
        sr = stats.get('StrikeRate', 0.0) or 0.0
        
        q = [f"What is {name}'s recent batting form?", f"How has {name} performed in their last {matches} matches?"]
        facts = f"[FACTS: Player: {name} | Last N Matches: {matches} | Runs: {runs} | Avg: {avg:.2f} | SR: {sr:.2f}]"
        
        if runs == 0:
            ans = random.choice([
                f"{name} is going through a completely dry spell, failing to score any runs in their last {matches} matches.",
                f"In a worrying stretch of form, {name} has 0 runs over the past {matches} games.",
                f"It's been a tough period for {name}, who hasn't troubled the scorers in their last {matches} appearances."
            ])
        elif runs < 20 and matches > 2:
            ans = f"Looking at the last {matches} matches, {name} is struggling for form. They have only managed {runs} runs at a low average of {avg:.2f}."
        elif sr > 130 and avg > 25:
            ans = f"{name} is in explosive form! In their last {matches} appearances, they have smashed {runs} runs at an impressive average of {avg:.2f}."
        else:
            ans = f"In recent outings ({matches} matches), {name} has scored {runs} runs, maintaining an average of {avg:.2f} with a strike rate of {sr:.2f}."
            
    else:
        wickets = stats.get('TotalWickets', 0) or 0
        econ = stats.get('EconomyRate', 0.0) or 0.0
        
        q = [f"What is {name}'s recent bowling form?", f"Is {name} bowling well recently?"]
        facts = f"[FACTS: Player: {name} | Last N Matches: {matches} | Wickets: {wickets} | Econ: {econ:.2f}]"
        
        if wickets == 0:
            ans = random.choice([
                f"{name} has struggled recently, going wicketless in their last {matches} matches.",
                f"Over the last {matches} games, {name} hasn't been able to take a single wicket.",
                f"It's been a tough patch for {name}, failing to strike in any of the last {matches} matches."
            ])
        elif wickets >= matches:
            ans = f"{name} is in excellent bowling form. Over their last {matches} matches, they have taken {wickets} wickets with a solid economy rate of {econ:.2f}."
        else:
            ans = f"Over the last {matches} matches, {name} has picked up {wickets} wickets. Their economy rate during this period is {econ:.2f}."
            
    return format_message(random.choice(q), facts, ans)

# --- NEW: Synthetic Data Generators to broaden scope (Narrative, Match Summary, Ball-by-Ball, Venue) ---

def generate_synthetic_match_summary():
    team1 = random.choice(["Lahore Qalandars", "Karachi Kings", "Peshawar Zalmi", "Islamabad United"])
    team2 = random.choice(["Multan Sultans", "Quetta Gladiators", "Rawalpindi Royals", "Faisalabad Wolves"])
    winner = random.choice([team1, team2])
    loser = team2 if winner == team1 else team1
    margin = random.choice([f"{random.randint(1, 50)} runs", f"{random.randint(1, 9)} wickets"])
    potm = random.choice(["Babar Azam", "Shaheen Afridi", "Shadab Khan", "Mohammad Rizwan"])
    
    q = random.choice([f"Who won between {team1} and {team2}?", f"Summarize the {team1} vs {team2} match."])
    f = f"[FACTS: Match: {team1} vs {team2} | Winner: {winner} | Margin: {margin} | Player of Match: {potm}]"
    
    a_templates = [
        f"{winner} emerged victorious against {loser} by a margin of {margin}. {potm} was named Player of the Match.",
        f"In that encounter, {winner} defeated {loser} by {margin}. The standout performer was {potm}.",
        f"It was a win for {winner}, who beat {loser} by {margin}. {potm} took home the Player of the Match honors."
    ]
    return format_message(q, f, random.choice(a_templates))

def generate_synthetic_narrative():
    player = random.choice(["Babar Azam", "Shaheen Afridi", "Rashid Khan", "Jos Buttler"])
    trait = random.choice(["cover drives", "yorkers", "spin variations", "explosive hitting"])
    impact = random.choice(["maintaining a high strike rate", "keeping a low economy", "taking crucial wickets", "anchoring the innings"])
    
    q = random.choice([f"Why is {player} so effective?", f"What makes {player} a great player?"])
    f = f"[FACTS: Player: {player} | Key Skill: {trait} | Impact: {impact}]"
    
    a_templates = [
        f"{player} is highly effective primarily due to their {trait}. This allows them to make a significant impact by {impact}.",
        f"The greatness of {player} stems from their exceptional {trait}. They consistently contribute to their team by {impact}.",
        f"If you look at {player}'s game, it's their {trait} that stands out, leading directly to them {impact}."
    ]
    return format_message(q, f, random.choice(a_templates))

def generate_synthetic_venue_stats():
    player = random.choice(["Fakhar Zaman", "Mohammad Rizwan", "Shadab Khan"])
    venue = random.choice(["Gaddafi Stadium", "National Stadium", "Rawalpindi Cricket Stadium"])
    matches = random.randint(5, 20)
    runs = matches * random.randint(20, 45)
    
    q = random.choice([f"How does {player} perform at {venue}?", f"Give me {player}'s stats at {venue}."])
    f = f"[FACTS: Player: {player} | Venue: {venue} | Matches: {matches} | Runs: {runs}]"
    
    a_templates = [
        f"{player} has a strong record at {venue}, scoring {runs} runs across {matches} matches.",
        f"At {venue}, {player} has played {matches} matches and accumulated {runs} runs.",
        f"Looking at the data for {venue}, {player} has stepped out {matches} times and tallied {runs} runs."
    ]
    return format_message(q, f, random.choice(a_templates))

def generate_synthetic_ball_by_ball():
    bowler = random.choice(["Naseem Shah", "Haris Rauf", "Imad Wasim"])
    batter = random.choice(["Virat Kohli", "Steve Smith", "Kane Williamson"])
    event = random.choice(["edged and taken at slip", "smashed for a massive six over long-on", "clean bowled through the gate", "driven for four through the covers"])
    
    q = random.choice([f"What happened on that ball between {bowler} and {batter}?", f"Describe the delivery from {bowler} to {batter}."])
    f = f"[FACTS: Bowler: {bowler} | Batter: {batter} | Outcome: {event}]"
    
    a_templates = [
        f"{bowler} bowled to {batter}, and the result was spectacular: the batter was {event}.",
        f"In that delivery, {batter} faced {bowler} and was {event}.",
        f"The outcome of {bowler}'s delivery to {batter} was that the ball was {event}."
    ]
    return format_message(q, f, random.choice(a_templates))

def main():
    conn = get_connection()
    dataset = []
    
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM v_clean_player")
            players = {p['PlayerId']: p for p in cur.fetchall()}
            
            cur.execute("SELECT * FROM v_player_career_batting")
            career_batting = {s['PlayerId']: s for s in cur.fetchall()}
            
            cur.execute("SELECT * FROM v_player_career_bowling")
            career_bowling = {s['PlayerId']: s for s in cur.fetchall()}
            
            cur.execute("SELECT * FROM v_player_recent_batting")
            recent_batting = {s['PlayerId']: s for s in cur.fetchall()}
            
            cur.execute("SELECT * FROM v_player_recent_bowling")
            recent_bowling = {s['PlayerId']: s for s in cur.fetchall()}
            
        print("Data loaded, generating conversational dataset...")
        
        # Real DB Generation loop
        player_ids = list(players.keys())
        for pid in player_ids:
            p = players[pid]
            if pid in career_batting:
                dataset.append(generate_batting_profile(p, career_batting[pid]))
            if pid in career_bowling:
                dataset.append(generate_bowling_profile(p, career_bowling[pid]))
            if pid in recent_batting:
                dataset.append(generate_recent_form(p, recent_batting[pid], "batting"))
            if pid in recent_bowling:
                dataset.append(generate_recent_form(p, recent_bowling[pid], "bowling"))
                
        # Inject Synthetic data for breadth (Scaling up to thousands)
        # Adding 1000 of each category creates 4000 varied examples, significantly boosting the fine-tune robustness.
        print("Generating synthetic scope-expansion examples...")
        for _ in range(1000):
            dataset.append(generate_synthetic_match_summary())
            dataset.append(generate_synthetic_narrative())
            dataset.append(generate_synthetic_venue_stats())
            dataset.append(generate_synthetic_ball_by_ball())
            
    finally:
        conn.close()

    random.shuffle(dataset)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item) + "\n")
            
    print(f"Successfully generated {len(dataset)} RAG-aligned samples in {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
