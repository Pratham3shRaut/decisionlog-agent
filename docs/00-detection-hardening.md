# Task: Decision-Detection Hardening (AI review)

**Status:** ✅ Implemented and tested (13/14 on the eval set)

## Goal

Reduce false positives in the AI that decides whether a message is a decision, and
catch multi-message decisions — the "AI review isn't done" gap.

## What was built

| File | Change |
|---|---|
| [`handlers/messages.py`](../handlers/messages.py) | Fetches up to 6–10 preceding messages (`conversations_replies` for threads, `conversations_history` for channel messages) and passes them as **context** to the detector. Previously `context` was always `None`. |
| [`gemini.py`](../gemini.py) | Hardened the detection prompt with explicit rules: questions, brainstorming, sarcasm, and hedging are **not** decisions; terse agreements ("+1", "sounds good") count **only** when context resolves what's being agreed to. |
| [`gemini.py`](../gemini.py) | Fixed a real bug: the `google-genai` SDK wraps failures in `tenacity.RetryError`, which hid the 429 message from our own retry logic — retries never fired. Now unwraps `.last_attempt.exception()` and raises the real error. |
| [`eval_detection.py`](../eval_detection.py) | 14-case labeled eval (positives, negatives, and context-dependent cases). |

## Testing performed

- ✅ `eval_detection.py`: **13/14**. The one miss was a **daily** Gemini quota
  exhaustion (free tier = 20 req/day on `gemini-2.5-flash`), not a detection error —
  that case simply couldn't run.

## Follow-up needed by the team

- Add the `channels:history` scope (+ `groups:history`/`im:history`/`mpim:history`
  for those conversation types) so context fetching works; reinstall the app.
- Use a paid Gemini key before demoing (free tier's 20 req/day is too low).
