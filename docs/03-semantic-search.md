# Task: Embeddings-Based Semantic Search (Q&A path)

**Status:** ✅ Implemented and tested (4/4 on the eval set)

## Goal

Make the `@DecisionLog why did we…?` Q&A path find the right decision by **meaning**,
not by recency. The previous implementation just grabbed the last 50 rows and stuffed
them into the prompt, so relevant-but-old decisions were silently missed once the log grew.

## What was built

| File | Change |
|---|---|
| [`gemini.py`](../gemini.py) | Added `embed_text(text)` (Gemini `gemini-embedding-001`, 3072-dim) and `cosine_similarity(a, b)`. |
| [`db.py`](../db.py) | Added a nullable `embedding` TEXT column (JSON-encoded vector) + a lightweight `init_db` migration that `ALTER TABLE`s it onto pre-existing tables. |
| [`handlers/actions.py`](../handlers/actions.py) | On **Confirm**, embeds `summary + rationale` and stores the vector alongside the decision. |
| [`handlers/mentions.py`](../handlers/mentions.py) | On a question, embeds the query, scores every decision with a stored embedding by cosine similarity, and passes the **top 8** to Gemini instead of the 50 most recent. |
| [`eval_semantic_search.py`](../eval_semantic_search.py) | Evaluation harness proving meaning-based ranking. |

## How ranking works

1. Question comes in → `embed_text(query)` produces a 3072-dim vector.
2. Every logged decision with a stored `embedding` is scored via
   `cosine_similarity(query_vector, decision_vector)`.
3. Top 8 decisions by score become the context for the answer LLM call.

## Design decisions

- **Embedding stored as JSON text**, not `pgvector`. Keeps the app portable across
  Postgres/SQLite with no DB extension; cosine similarity is computed in Python.
  For the challenge's data volume this is more than fast enough.
- **Everything degrades gracefully.** If the query embedding fails, or no rows have
  embeddings yet (e.g. decisions logged before this feature), the code **falls back
  to recency-based context** and logs that it did. Embedding failure never blocks
  logging a decision.
- **Model:** `gemini-embedding-001` — chosen after confirming `text-embedding-004`
  is not served on this API version; `gemini-embedding-001` is the stable current model.

## Testing performed

- ✅ `python -m py_compile` on all changed files.
- ✅ **Live DB migration** ran against the real database; confirmed the `embedding`
  column now exists on `logged_decisions`.
- ✅ **Semantic ranking eval** ([`eval_semantic_search.py`](../eval_semantic_search.py)):
  **4/4** — each question ranked the correct decision first *despite no keyword overlap*:

  | Question | Correctly ranked decision | Score |
  |---|---|---|
  | "why did we move the release date?" | "…deploy the launch on Friday instead of Monday…" | 0.720 |
  | "what database are we using and why?" | "…chose PostgreSQL over MongoDB…" | 0.708 |
  | "did we cut any features for the first version?" | "…dropping the dark mode feature from v1…" | 0.733 |
  | "how are we handling payments?" | "…use Stripe as our payment processor." | 0.713 |

## Notes / limitations

- Decisions logged **before** this feature have no embedding and will only appear
  via the recency fallback. Optional future task: a backfill script to embed old rows.
- Gemini free tier caps embedding + generation requests; a paid key is recommended
  before the live demo.
