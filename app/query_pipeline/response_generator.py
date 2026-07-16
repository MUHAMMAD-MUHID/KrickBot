"""
Response Generator — final LLM response generation using Groq API.

Takes the user's question + retrieved context (SQL result or RAG documents)
and generates a natural-language response using the Groq API (Llama 3).
"""
from groq import Groq
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize Groq client
client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

def generate_response(query: str, context: str, intent: str = "FACTUAL") -> str:
    """
    Generates a natural language response using Groq based on the query and context.
    """
    if not client:
        logger.error("Groq API key not found in settings.")
        return "Error: LLM provider is not configured properly."
        
    system_prompt = (
        "You are KrickBot, an analytical cricket assistant. "
        "Answer the user's question using ONLY the provided context/facts. "
        "Write naturally and avoid robotic repetition."
    )
    
    if intent == "FACTUAL":
        system_prompt += " The context contains database SQL query results."
    elif intent == "EXPLANATORY":
        system_prompt += " The context contains retrieved documents."
    elif intent == "CHITCHAT":
        system_prompt = "You are KrickBot, a friendly cricket chatbot. Keep your answers brief and conversational."
        
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
            ],
            temperature=0.7,
            max_tokens=512,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error generating response from Groq: {str(e)}")
        return "I'm sorry, I encountered an error while generating the response."
