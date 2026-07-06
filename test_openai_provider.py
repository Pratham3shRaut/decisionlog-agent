"""
Live smoke test for the OpenAI provider. Run AFTER setting OPENAI_API_KEY in .env.

    LLM_PROVIDER=openai python test_openai_provider.py
    (or set LLM_PROVIDER=openai in .env, then: python test_openai_provider.py)

Exercises all three provider functions: detect_decision, embed_text, answer_query.
"""
import llm


def main():
    print(f"Provider: {llm.PROVIDER}\n")

    # 1. Detection: a clear decision and a clear non-decision.
    d = llm.detect_decision("Agreed, let's ship on Friday instead of Monday.")
    print(f"[detect] is_decision={d.is_decision} summary={d.summary!r}")
    assert d.is_decision is True, "expected a decision"

    q = llm.detect_decision("Should we go with Postgres or Mongo?")
    print(f"[detect] is_decision={q.is_decision} (question, expect False)")
    assert q.is_decision is False, "question should not be a decision"

    # 2. Embedding + ranking.
    corpus = [
        "We chose PostgreSQL over MongoDB because our data is relational.",
        "We will deploy on Friday instead of Monday for more QA time.",
    ]
    vecs = [llm.embed_text(c) for c in corpus]
    assert all(v for v in vecs), "embeddings should be returned"
    qv = llm.embed_text("what database did we pick?")
    scores = [llm.cosine_similarity(qv, v) for v in vecs]
    top = scores.index(max(scores))
    print(f"[embed] top match for 'what database': {corpus[top]!r}")
    assert top == 0, "database question should match the Postgres decision"

    # 3. Q&A.
    ans = llm.answer_query(
        "why did we pick our database?",
        [{"summary": corpus[0], "rationale": "relational data", "decision_maker": "Team", "created_at": "2026-07-01"}],
    )
    print(f"[answer] {ans[:120]}...")
    assert ans, "expected a non-empty answer"

    print("\nAll OpenAI provider checks passed.")


if __name__ == "__main__":
    main()
