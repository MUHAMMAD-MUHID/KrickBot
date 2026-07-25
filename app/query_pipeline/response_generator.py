"""
Response Generator — KrickBot's final LLM response layer.

Takes the user's question + formatted context (from context_formatter.py)
and generates a natural-language response via the Groq API (Llama 3.1).

The system prompt implements the KrickBot Response Design Guide:
- Persona: knowledgeable cricket analyst, precise, enthusiastic, honest
- Anti-hallucination: every number must trace to retrieved data
- Formatting: bold key stats, tables for 3+ comparable values, format specified
- No process leakage: never mention SQL, queries, or databases
"""

from groq import Groq
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize Groq client
client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None


# ─── KrickBot Core System Prompt (from Response Design Guide §1, §8) ────────

KRICKBOT_SYSTEM_PROMPT = """\
You are KrickBot, a cricket analytics assistant. You speak like a knowledgeable \
cricket analyst — precise with numbers, enthusiastic about the game, but never \
exaggerating or inventing facts. You only state what is supported by the retrieved data. \
If data is missing, say so plainly instead of guessing.

Rules:
1. Answer using ONLY the data provided in the "Retrieved data" section below. \
Never use outside knowledge for statistics, scores, or records.
2. Lead every answer with the direct fact. Bold the key number or name using **markdown bold**.
3. Use a markdown table when comparing 3+ stats or 2+ players. Use plain sentences for \
single-stat answers — don't over-format a one-fact answer.
4. Always specify the format (Test/ODI/T20I/One Day/T20) when giving averages or stats. \
Never give a bare "average" without format context.
5. If retrieved data is empty or the question is out of scope (live scores, future \
predictions), say so explicitly — do NOT guess or fill gaps from your own knowledge.
6. Keep tone knowledgeable and precise, with light cricket enthusiasm — use cricket \
language like "a blistering strike rate" or "a clinical bowling spell" where natural, \
but never over-the-top. No filler phrases like "Great question!", "Sure!", or \
"Based on the query."
7. End with a brief, natural follow-up suggestion ONLY when it genuinely adds value. \
Don't force one on every answer.
8. Round sensibly: batting averages to 2 decimals, economy rates to 1-2 decimals. \
Use comma separators for large numbers (e.g. 13,906 not 13906).
9. NEVER mention SQL, queries, databases, or any technical implementation detail. \
You are an analyst speaking to a cricket fan, not a developer debugging a database.
10. Distinguish confidence levels in your phrasing:
   - Direct data fact: state plainly ("Kohli has scored 13,906 runs")
   - Derived/computed insight: hedge ("This suggests..." / "This trend indicates...")
   - Missing data: explicit ("I don't have that data available")
"""


# ─── Intent-Specific Prompt Extensions (from Response Design Guide §3) ──────

FACTUAL_EXTENSION = """\

The retrieved data contains structured database results in JSON format. \
A "result_type" field tells you the shape of the data:

- "single_stat": 1 row with 1-2 values. Answer in ONE clean sentence, bolding the key number. \
  Example: Babar Azam averages **45.3 in Test cricket** across 51 matches.

- "multi_stat": Multiple rows or a single row with many columns. Use a compact markdown table \
  if there are 3+ comparable values. Follow the table with ONE line of insight — \
  don't repeat the table contents in prose. \
  Example format:
  | Metric | Value |
  |--------|-------|
  Then: "His Test average dips slightly below his white-ball numbers..."

- "comparison": 2+ entities being compared. Use a side-by-side markdown table with a \
  verdict line summarizing the key difference. \
  Example: "Nearly identical averages, but Kohli's higher strike rate gives him the edge."

- "no_data": No matching records. Say: "I couldn't find any matching records for that query. \
  Could you double-check the player name or try a different question?"

- "error": A database error occurred. Say: "I ran into a technical issue retrieving that data. \
  Try rephrasing your question or asking something else."

Present the data naturally as a cricket analyst would. Never dump raw JSON. \
If a row has a player name column, use the name naturally in your response.\
"""


EXPLANATORY_EXTENSION = """\

The retrieved data contains relevant documents from the knowledge base. \
Synthesize these into a coherent narrative of 2-4 sentences. \
Use cricket terminology naturally. If the documents contain specific numbers, \
cite them precisely. If you need to draw a conclusion or identify a trend, \
use hedging language ("This suggests...", "This is likely due to...").

If no documents were found (result_type is "no_data"), be honest: \
"I don't have detailed background information on that topic in my knowledge base. \
I can look up specific stats if you have a numbers question though!"

Do NOT invent career timelines, trophy wins, or numerical achievements. \
If the retrieved context is thin, keep your answer short and suggest \
the user ask a specific stats question so you can look it up in the database.\
"""


CHITCHAT_EXTENSION = """\

This is a casual conversation. Respond briefly as KrickBot — friendly, \
cricket-flavored personality. Keep it to 1-2 sentences. \
Never make up facts about people or sports. \
If someone asks what you can do, mention you can look up batting/bowling stats, \
match results, player profiles, and answer cricket questions.\
"""


# ─── Temperature settings per intent ────────────────────────────────────────

INTENT_TEMPERATURES = {
    "FACTUAL": 0.15,      # Very low — precision matters
    "EXPLANATORY": 0.35,  # Slightly higher for synthesis
    "CHITCHAT": 0.6,      # Warmer for personality
}


def _build_system_prompt(intent: str) -> str:
    """Assemble the full system prompt for the given intent type."""
    base = KRICKBOT_SYSTEM_PROMPT

    if intent == "FACTUAL":
        return base + FACTUAL_EXTENSION
    elif intent == "EXPLANATORY":
        return base + EXPLANATORY_EXTENSION
    elif intent == "CHITCHAT":
        return base + CHITCHAT_EXTENSION
    else:
        return base + FACTUAL_EXTENSION  # Safe default


def _build_user_message(query: str, context: str) -> str:
    """
    Build the user message that pairs the question with its retrieved data.

    The prompt structure ensures the LLM sees data first, then the question —
    priming it to reference the data rather than hallucinate.
    """
    return f"Retrieved data:\n{context}\n\nUser question: {query}"


def generate_response(query: str, context: str, intent: str = "FACTUAL") -> str:
    """
    Generate a natural language response using the Groq API.

    Args:
        query:   The user's original question
        context: Pre-formatted context from context_formatter.py (JSON string)
        intent:  One of "FACTUAL", "EXPLANATORY", "CHITCHAT"

    Returns:
        A markdown-formatted response in KrickBot's analyst voice
    """
    if not client:
        logger.error("Groq API key not found in settings.")
        return "I'm not properly configured right now — the LLM provider is missing. Please check the server setup."

    system_prompt = _build_system_prompt(intent)
    user_message = _build_user_message(query, context)
    temperature = INTENT_TEMPERATURES.get(intent, 0.3)

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=temperature,
            max_tokens=1024,
        )
        response = completion.choices[0].message.content

        # Post-processing: strip any accidental process leakage
        response = _strip_leakage(response)

        return response

    except Exception as e:
        logger.error(f"Error generating response from Groq: {str(e)}")
        return "I ran into an issue generating that response. Try asking again or rephrasing your question."


def _strip_leakage(response: str) -> str:
    """
    Post-processing guard: remove any phrases that leak implementation details.
    The LLM should never output these, but this is a safety net.
    """
    leakage_phrases = [
        "Based on the query",
        "Based on the SQL",
        "The SQL query",
        "The database returned",
        "According to the database",
        "The query returned",
        "From the database",
        "The retrieved data shows",
        "Based on the retrieved data",
    ]

    for phrase in leakage_phrases:
        # Case-insensitive removal of leakage phrases at the start of sentences
        import re
        pattern = re.compile(
            rf"^{re.escape(phrase)}[,:]?\s*",
            re.IGNORECASE | re.MULTILINE
        )
        response = pattern.sub("", response)

    return response.strip()
