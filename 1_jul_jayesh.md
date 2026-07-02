# Implementation Plan - DecisionLog Slack Agent (Python/FastAPI)

This plan outlines the design, architecture, and implementation details for building **DecisionLog** using Python, FastAPI, Slack Bolt for Python, and the Google Gemini API with Neon PostgreSQL.

## Design Decisions (Approved)

> [!IMPORTANT]
> **API & Agent Tech Stack**: The API and background agent will be built using Python 3.10+, FastAPI, and `slack-bolt` running asynchronously via `AsyncSocketModeHandler` in the FastAPI lifespan.
> * **Database ORM**: **SQLAlchemy** will be used to manage models and database interactions.
> * **LLM Model**: **`gemini-1.5-flash`** (via the new `google-genai` SDK) will be used for decision detection and Q&A.

---

## Proposed Changes

### 1. Dependencies (`requirements.txt`)

We will create a `requirements.txt` with:
* `fastapi`
* `uvicorn[standard]`
* `slack-bolt`
* `google-genai`
* `sqlalchemy`
* `psycopg2-binary`
* `python-dotenv`

---

### 2. File Structure

We will create a clean Python structure:

```
decisionlog-agent/
├── requirements.txt
├── .env
├── .gitignore
├── main.py               # Entry point: initializes FastAPI, lifespan, and Bolt
├── db.py                 # SQLAlchemy database setup (Session, Engine, Models)
├── gemini.py             # Google Gemini client for decision detection & Q&A
└── handlers/
    ├── __init__.py       # Registers Slack handlers to the Bolt app
    ├── messages.py       # Listen to messages in channels & call Gemini to detect decisions
    ├── actions.py        # Handle button clicks (Confirm / Dismiss) from block kit cards
    └── mentions.py       # Handle `@DecisionLog` app mentions for answering questions
```

---

### 3. Execution Logic Flow

#### Step A: Async Socket Mode inside FastAPI
We will run the Bolt Socket Mode handler asynchronously using FastAPI's `lifespan` context manager:
```python
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from slack_bolt.app import App
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

bolt_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Socket Mode handler in a background task
    handler = AsyncSocketModeHandler(bolt_app, os.environ.get("SLACK_APP_TOKEN"))
    asyncio.create_task(handler.start_async())
    yield
    # Cleanup connections on shutdown

app = FastAPI(lifespan=lifespan)
```

#### Step B: Real-Time Detection
1. In `handlers/messages.py`, the app listens to all channel messages:
   ```python
   @bolt_app.event("message")
   async def handle_message_events(event, say, client):
       # Process message text with Gemini
   ```
2. Gemini checks if the message constitutes a team decision.
3. If yes, it returns structured JSON detailing:
   * `summary` (what was decided)
   * `rationale` (why it was decided)
   * `decision_maker` (who decided it)
4. We send an interactive Slack **Block Kit card** in the thread with **Confirm** and **Dismiss** buttons.

#### Step C: One-Click Confirmation
1. Clicking **Confirm** triggers a block action callback in `handlers/actions.py`.
2. The decision is saved to the PostgreSQL database using SQLAlchemy.
3. The Slack card in the thread is updated to show: `"Decision Logged Successfully!"`.

#### Step D: Search & Q&A
1. When `@DecisionLog` is mentioned in a channel (handled in `handlers/mentions.py`), we extract the query.
2. We query PostgreSQL via SQLAlchemy to retrieve relevant logged decisions.
3. We feed the relevant logs as context to Gemini (`gemini-1.5-flash`), generating a helpful response.
4. We post the response in the thread.

---

## Verification Plan

### Automated Tests
- Run database connection check.
- Test Gemini API key connection.

### Manual Verification
- Start FastAPI with `uvicorn main:app --reload`.
- In a test Slack channel, write a decision (e.g. *"We decided to use Postgres because of scale"*).
- Confirm the Block Kit card is posted.
- Click **Confirm** and verify that it is written to PostgreSQL.
- Mention `@DecisionLog why did we use Postgres?` and verify the correct response.
