"""
Evaluation for embeddings-based semantic search (gemini.py::embed_text + cosine_similarity).

Proves the Q&A path ranks decisions by MEANING, not keyword overlap: a query that
shares no keywords with the correct decision should still rank it first.

Run: python eval_semantic_search.py   (needs GEMINI_API_KEY; uses ~6 embedding calls)
"""
import sys
import time
from llm import embed_text, cosine_similarity

# A small corpus of "logged decisions".
DECISIONS = [
    "We will deploy the launch on Friday instead of Monday to give QA more buffer time.",
    "We chose PostgreSQL over MongoDB because our data is highly relational.",
    "We are dropping the dark mode feature from the v1 release due to time constraints.",
    "The team agreed to use Stripe as our payment processor.",
]

# (question, index of the decision that SHOULD rank first, note)
QUERIES = [
    ("why did we move the release date?", 0, "no shared keywords with 'deploy on Friday' decision"),
    ("what database are we using and why?", 1, "'database' vs 'PostgreSQL/MongoDB'"),
    ("did we cut any features for the first version?", 2, "'cut features' vs 'dropping dark mode'"),
    ("how are we handling payments?", 3, "'payments' vs 'Stripe payment processor'"),
]


def run():
    print("Embedding decision corpus...")
    decision_vectors = []
    for d in DECISIONS:
        decision_vectors.append(embed_text(d))
        time.sleep(1)

    passed = 0
    for question, expected_idx, note in QUERIES:
        qv = embed_text(question)
        time.sleep(1)
        if qv is None:
            print(f"[ERROR] could not embed query: {question}")
            continue
        scores = [(cosine_similarity(qv, dv) if dv else -1.0, i) for i, dv in enumerate(decision_vectors)]
        scores.sort(reverse=True)
        top_idx = scores[0][1]
        ok = top_idx == expected_idx
        passed += int(ok)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] Q: \"{question}\"")
        print(f"        top match: \"{DECISIONS[top_idx]}\" (score={scores[0][0]:.3f})")
        print(f"        expected:  \"{DECISIONS[expected_idx]}\" ({note})")

    print("\n" + "=" * 60)
    print(f"Semantic ranking accuracy: {passed}/{len(QUERIES)}")
    return 0 if passed == len(QUERIES) else 1


if __name__ == "__main__":
    sys.exit(run())
