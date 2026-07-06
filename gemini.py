import os
import json
import time
from typing import List, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Shared, provider-agnostic schema / prompts / math.
from llm_common import (
    DecisionAnalysis,
    build_detection_prompt,
    build_qa_prompt,
    cosine_similarity,  # re-exported so existing `from gemini import cosine_similarity` still works
)

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

def detect_decision(
    text: str,
    context: Optional[str] = None,
    sender_name: Optional[str] = None,
    current_date: Optional[str] = None
) -> DecisionAnalysis:
    """
    Analyzes a message text (with optional preceding context, sender name, and current date) to determine if a decision was made.
    """
    prompt = build_detection_prompt(text, context=context, sender_name=sender_name, current_date=current_date)

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


def answer_query(query: str, logs: List[dict], current_date: Optional[str] = None) -> str:
    """
    Generates an answer to a user's question about past decisions, using the logged decisions as context.
    """
    prompt = build_qa_prompt(query, logs, current_date=current_date)

    response = generate_content_with_retry(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
        ),
    )
    return response.text.strip()
