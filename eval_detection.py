"""
Standalone evaluation script for the decision-detection prompt (gemini.py::detect_decision).

Run: python eval_detection.py

Measures precision/recall against a small hand-labeled set of Slack-style messages,
including tricky negatives (questions, sarcasm, brainstorming) that should NOT trigger
a decision card, and positives that require conversational context to catch.

This does not require a live Slack connection, only GEMINI_API_KEY in .env.
"""
import sys
import time
from gemini import detect_decision

# Free-tier Gemini quota is 5 requests/minute; space calls out to avoid burning the whole
# budget on retries (each retry-after-429 already costs ~15-50s).
SECONDS_BETWEEN_CALLS = 13

# Each case: (text, context, expected_is_decision, note)
CASES = [
    # --- Clear positives ---
    ("We'll go with Postgres instead of MongoDB, it's the better fit for our relational data.", None, True, "explicit decision + rationale"),
    ("Agreed, let's ship on Friday instead of Monday.", None, True, "explicit agreement"),
    ("Ok let's drop the dark mode feature for v1, not enough time.", None, True, "decision + rationale"),
    ("Alright, final call: we're using Stripe for payments.", None, True, "explicit finality"),

    # --- Positives requiring context ---
    (
        "Sounds good, let's do that.",
        "<@U1>: should we move the launch to next Wednesday?\n<@U2>: I think that works, gives us more buffer.",
        True,
        "agreement message alone is ambiguous without context",
    ),
    (
        "+1",
        "<@U1>: proposing we cut the Jira integration from scope for this sprint\n<@U2>: agreed, cutting it",
        True,
        "terse agreement needs context to resolve what was agreed",
    ),

    # --- Clear negatives ---
    ("Should we go with Postgres or Mongo?", None, False, "question, not a decision"),
    ("What do you all think about moving the launch date?", None, False, "soliciting opinions"),
    ("lol yeah sure, totally, let's rewrite everything in COBOL", None, False, "sarcasm"),
    ("Just brainstorming here — maybe we could try Redis for caching?", None, False, "brainstorm/proposal without agreement"),
    ("Has anyone looked at the Postgres migration yet?", None, False, "status question"),
    ("I'm leaning towards Friday but not sure yet, thoughts?", None, False, "leaning, not decided"),
    ("lgtm", None, False, "generic ack with no decision content, no context"),

    # --- Negatives that need context to correctly reject ---
    (
        "yeah maybe",
        "<@U1>: should we consider rewriting the whole backend in Rust?",
        False,
        "noncommittal response to a big hypothetical, not a real decision",
    ),
]


def run():
    total = len(CASES)
    correct = 0
    false_positives = []
    false_negatives = []

    for i, (text, context, expected, note) in enumerate(CASES):
        if i > 0:
            time.sleep(SECONDS_BETWEEN_CALLS)
        try:
            result = detect_decision(text, context=context, sender_name="Alex", current_date="Saturday, July 4, 2026")
        except Exception as e:
            print(f"[ERROR] '{text}' -> exception: {e}")
            continue

        got = result.is_decision
        ok = got == expected
        correct += int(ok)

        status = "PASS" if ok else "FAIL"
        print(f"[{status}] expected={expected} got={got} | \"{text}\" ({note})")
        if got and not expected:
            false_positives.append((text, note))
        if not got and expected:
            false_negatives.append((text, note))

    print("\n" + "=" * 60)
    print(f"Accuracy: {correct}/{total} ({100 * correct / total:.0f}%)")
    if false_positives:
        print(f"\nFalse positives ({len(false_positives)}):")
        for text, note in false_positives:
            print(f"  - \"{text}\" ({note})")
    if false_negatives:
        print(f"\nFalse negatives ({len(false_negatives)}):")
        for text, note in false_negatives:
            print(f"  - \"{text}\" ({note})")

    return 0 if correct == total else 1


if __name__ == "__main__":
    sys.exit(run())
