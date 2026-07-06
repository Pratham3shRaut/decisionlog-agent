# Task: Multi-Provider LLM Abstraction (Gemini + OpenAI)

**Status:** ✅ Implemented; Gemini path tested, OpenAI path pending live key

## Goal

Let DecisionLog run on **either Gemini or OpenAI** via a single `.env` switch — no
code changes. Primary motivation: Gemini's free tier caps at 20 requests/day, which
blocks testing and would kill a live demo. An OpenAI key sidesteps that.

## What was built

| File | Role |
|---|---|
| [`llm_common.py`](../llm_common.py) | Provider-agnostic shared pieces: the `DecisionAnalysis` schema, the detection prompt, the Q&A prompt, and `cosine_similarity`. Both providers reuse these, so prompts/schema are identical across providers. |
| [`gemini.py`](../gemini.py) | Gemini implementation (`detect_decision` / `answer_query` / `embed_text`), refactored to import shared prompts/schema from `llm_common`. |
| [`openai_provider.py`](../openai_provider.py) | OpenAI implementation using the OpenAI SDK v1+ (`chat.completions.parse` for structured detection, `embeddings.create` for vectors). |
| [`llm.py`](../llm.py) | Dispatcher. Reads `LLM_PROVIDER` and re-exports the chosen provider's functions. |

All app code now imports from **`llm`**, not `gemini`:
`from llm import detect_decision, answer_query, embed_text, cosine_similarity, DecisionAnalysis`.

## How to switch providers

In `.env`:
```
LLM_PROVIDER=openai        # or: gemini (default)
OPENAI_API_KEY=sk-...
# optional: OPENAI_CHAT_MODEL=gpt-4o-mini
# optional: OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```
No code edits. Restart the app.

## Model defaults

| | Gemini | OpenAI |
|---|---|---|
| Chat / detection | `gemini-2.5-flash` | `gpt-4o-mini` |
| Embeddings | `gemini-embedding-001` (3072-dim) | `text-embedding-3-small` (1536-dim) |

> Note: embedding **dimensions differ between providers**. Embeddings are only ever
> compared against other embeddings from the *same* provider, so cosine similarity is
> consistent within a deployment. If you switch providers after logging decisions,
> re-embed old rows (or expect them to fall back to recency ranking).

## Testing performed

- ✅ Full compile of all modules.
- ✅ Default (`gemini`) import: dispatcher selects Gemini, all functions resolve.
- ✅ `LLM_PROVIDER=openai`: dispatcher routes every function to `openai_provider`,
  and raises a clean `RuntimeError` (not a crash) when `OPENAI_API_KEY` is absent.
- ⏳ **Live OpenAI calls**: run `test_openai_provider.py` once your key is set.

## To finish (team)

1. Put `OPENAI_API_KEY=sk-...` and `LLM_PROVIDER=openai` in `.env`.
2. Run:
   ```
   python test_openai_provider.py
   ```
   Expect "All OpenAI provider checks passed." Then re-run `eval_detection.py` /
   `eval_semantic_search.py` to confirm quality on OpenAI (no daily-quota wall).
