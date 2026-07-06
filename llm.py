"""
Provider-agnostic LLM entry point for DecisionLog.

Selects the backend via the LLM_PROVIDER environment variable:
    LLM_PROVIDER=gemini   (default)  -> gemini.py   (Google Gemini)
    LLM_PROVIDER=openai              -> openai_provider.py (OpenAI)

All application code should `from llm import detect_decision, answer_query, embed_text, cosine_similarity, DecisionAnalysis`
so switching providers is a one-line .env change with no code edits.
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("decisionlog.llm")

PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()

if PROVIDER == "openai":
    import openai_provider as _impl
    logger.info("LLM provider: OpenAI")
elif PROVIDER == "gemini":
    import gemini as _impl
    logger.info("LLM provider: Gemini")
else:
    raise ValueError(f"Unknown LLM_PROVIDER '{PROVIDER}'. Use 'gemini' or 'openai'.")

# Re-export the unified interface from the selected provider.
from llm_common import DecisionAnalysis, cosine_similarity  # schema + math are provider-agnostic

detect_decision = _impl.detect_decision
answer_query = _impl.answer_query
embed_text = _impl.embed_text

__all__ = ["detect_decision", "answer_query", "embed_text", "cosine_similarity", "DecisionAnalysis", "PROVIDER"]
