import os
import json
import time
from typing import List, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini Client
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def generate_content_with_retry(model: str, contents: str, config: types.GenerateContentConfig, max_retries: int = 3, initial_delay: float = 15.0):
    """
    Wrapper around client.models.generate_content that catches rate limit errors (429)
    and automatically retries with exponential backoff.
    """
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config
            )
        except Exception as e:
            # The google-genai SDK wraps its own internal retries in tenacity.RetryError,
            # which hides the real ClientError (and its 429 message) inside .last_attempt.
            underlying = e
            if hasattr(e, "last_attempt"):
                try:
                    underlying = e.last_attempt.exception() or e
                except Exception:
                    underlying = e
            err_str = str(underlying)
            is_rate_limit = any(term in err_str for term in ("429", "ResourceExhausted", "Too Many Requests", "Quota exceeded", "RESOURCE_EXHAUSTED"))
            if is_rate_limit and attempt < max_retries:
                print(f"Gemini API rate limited (429). Retrying in {delay:.1f}s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                # Re-raise the underlying exception so callers see the real error, not tenacity's RetryError
                raise underlying

# Pydantic schema for structured decision detection
class DecisionAnalysis(BaseModel):
    is_decision: bool = Field(
        description="True if the message represents a clear decision, agreement, resolution, or plan of action. False if it is just a question, normal conversation, brainstorming, or proposal without agreement."
    )
    summary: Optional[str] = Field(
        default=None,
        description="A concise summary of what was decided (e.g., 'We will deploy the feature on Friday'). If the message uses first-person pronouns like 'I' or 'my', resolve them to the Message Sender's name if provided. If the message refers to relative dates like 'tomorrow', 'today', or days of the week, resolve them to absolute dates (e.g. 'July 2, 2026') using the Current Date. Leave empty if is_decision is False."
    )
    rationale: Optional[str] = Field(
        default=None,
        description="The reason, explanation, or context for why this decision was made. If the message uses first-person pronouns like 'I' or 'my' in the explanation, resolve them to the Message Sender's name. Resolve any relative dates to absolute dates using the Current Date. Leave empty if is_decision is False or no explanation is provided."
    )
    decision_maker: Optional[str] = Field(
        default=None,
        description="The name or user ID of the person who made the decision, or 'Team' if it was a group agreement. Prefer using the Message Sender's name if the decision is individual. Leave empty if is_decision is False."
    )

def detect_decision(
    text: str, 
    context: Optional[str] = None, 
    sender_name: Optional[str] = None,
    current_date: Optional[str] = None
) -> DecisionAnalysis:
    """
    Analyzes a message text (with optional preceding context, sender name, and current date) to determine if a decision was made.
    """
    sender_info = f"Message Sender: {sender_name}\n" if sender_name else ""
    date_info = f"Current Date: {current_date}\n" if current_date else ""
    rules = """
    Rules:
    - Only mark is_decision=True if the team has actually settled on a course of action.
    - Questions, requests for opinions, and status checks ("should we...?", "what do you think?", "has anyone looked at...?") are NOT decisions.
    - Brainstorming and proposals without agreement ("maybe we could try...", "just an idea") are NOT decisions.
    - Sarcastic or joking messages are NOT decisions, even if phrased like one.
    - Noncommittal or hedging responses ("yeah maybe", "leaning towards", "not sure yet") are NOT decisions.
    - A short agreement like "agreed", "+1", "sounds good", or "let's do that" IS a decision, but only if the
      Recent Conversation Context makes clear what specific proposal is being agreed to. If there is no context
      and the message alone is ambiguous, mark is_decision=False.
    - Generic acknowledgements with no decision content ("lgtm", "ok", "thanks") are NOT decisions.
    """
    prompt = f"""
    Analyze the following Slack message to determine if a team decision, resolution, or finalized plan of action has occurred.
    {rules}
    {sender_info}{date_info}Current Message:
    "{text}"
    """
    if context:
        prompt = f"""
        Recent Conversation Context:
        {context}
        {rules}
        {sender_info}{date_info}Current Message:
        "{text}"
        """

    response = generate_content_with_retry(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DecisionAnalysis,
            temperature=0.1,  # Low temperature for deterministic analysis
        ),
    )
    
    # The response text will be a JSON string conforming to DecisionAnalysis
    data = json.loads(response.text)
    return DecisionAnalysis(**data)

EMBEDDING_MODEL = "gemini-embedding-001"


def embed_text(text: str) -> Optional[List[float]]:
    """
    Return a semantic embedding vector for the given text, or None on failure.
    Used to store one embedding per logged decision and to embed incoming
    questions for semantic (meaning-based) search in the Q&A path.
    """
    if not text or not text.strip():
        return None
    try:
        response = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
        return list(response.embeddings[0].values)
    except Exception as e:
        # Unwrap tenacity RetryError to log the real cause, but never let embedding
        # failure break decision logging — semantic search simply degrades.
        underlying = e
        if hasattr(e, "last_attempt"):
            try:
                underlying = e.last_attempt.exception() or e
            except Exception:
                underlying = e
        print(f"Embedding failed (semantic search will be degraded): {underlying}")
        return None


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two equal-length vectors. Returns 0.0 if either is empty/mismatched."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def answer_query(query: str, logs: List[dict], current_date: Optional[str] = None) -> str:
    """
    Generates an answer to a user's question about past decisions, using the logged decisions as context.
    """
    # Format logs as a readable context
    formatted_logs = ""
    for idx, log in enumerate(logs, 1):
        formatted_logs += f"{idx}. Decision: {log.get('summary')}\n"
        if log.get('rationale'):
            formatted_logs += f"   Why: {log.get('rationale')}\n"
        if log.get('decision_maker'):
            formatted_logs += f"   Who: {log.get('decision_maker')}\n"
        formatted_logs += f"   Date: {log.get('created_at')}\n\n"

    date_info = f"Current Date of Question: {current_date}\n" if current_date else ""
    prompt = f"""
    You are the DecisionLog Assistant. A user is asking a question about past team decisions.
    Use the following logged decisions as context to answer their question accurately.
    
    {date_info}If the context does not contain the answer, say that you couldn't find any relevant decisions logged for that query.
    Keep the tone professional, helpful, and concise.

    Logged Decisions Context:
    {formatted_logs if formatted_logs else "No matching decisions found."}

    User Question:
    "{query}"
    """

    response = generate_content_with_retry(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
        ),
    )
    return response.text.strip()
