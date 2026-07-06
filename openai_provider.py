"""
OpenAI implementation of the LLM interface (detect_decision / answer_query / embed_text).

Selected when LLM_PROVIDER=openai. Uses the OpenAI Python SDK v1+:
  - chat.completions.parse for structured decision detection (Pydantic-typed output)
  - chat.completions.create for Q&A
  - embeddings.create for semantic-search vectors
"""
import os
import time
import logging
from typing import List, Optional

from openai import OpenAI
from dotenv import load_dotenv

from llm_common import (
    DecisionAnalysis,
    build_detection_prompt,
    build_qa_prompt,
    cosine_similarity,  # re-exported for callers that import from here
)

load_dotenv()

logger = logging.getLogger("decisionlog.openai")

CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

_api_key = os.environ.get("OPENAI_API_KEY")
_client = OpenAI(api_key=_api_key) if _api_key else None


def _require_client():
    if _client is None:
        raise RuntimeError("OPENAI_API_KEY is not set but LLM_PROVIDER=openai.")
    return _client


def _with_retry(fn, max_retries: int = 3, initial_delay: float = 2.0):
    """Retry on rate-limit / transient errors with exponential backoff."""
    delay = initial_delay
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = any(t in err_str for t in ("rate limit", "429", "too many requests", "overloaded"))
            if is_rate_limit and attempt < max_retries:
                logger.warning(f"OpenAI rate limited. Retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(delay)
                delay *= 2
            else:
                raise


def detect_decision(text, context=None, sender_name=None, current_date=None) -> DecisionAnalysis:
    client = _require_client()
    prompt = build_detection_prompt(text, context=context, sender_name=sender_name, current_date=current_date)

    def _call():
        completion = client.chat.completions.parse(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You classify Slack messages as decisions and extract structured fields."},
                {"role": "user", "content": prompt},
            ],
            response_format=DecisionAnalysis,
            temperature=0.1,
        )
        return completion.choices[0].message.parsed

    result = _with_retry(_call)
    # Guard against a rare refusal / null parse.
    return result if result is not None else DecisionAnalysis(is_decision=False)


def answer_query(query: str, logs: List[dict], current_date: Optional[str] = None) -> str:
    client = _require_client()
    prompt = build_qa_prompt(query, logs, current_date=current_date)

    def _call():
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return completion.choices[0].message.content

    return (_with_retry(_call) or "").strip()


def embed_text(text: str) -> Optional[List[float]]:
    if not text or not text.strip():
        return None
    client = _require_client()

    def _call():
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        return list(response.data[0].embedding)

    try:
        return _with_retry(_call)
    except Exception as e:
        logger.warning(f"OpenAI embedding failed (semantic search degraded): {e}")
        return None
