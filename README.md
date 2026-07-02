# decisionlog-agent
# DecisionLog

> A Slack agent that detects decisions in conversation and documents them automatically.

Built for the [Slack Agent Builder Challenge](https://slack-agent-builder.devpost.com).

---

## The problem

Every team's most important decisions happen in Slack — "let's ship Friday instead of Monday", "we'll go with Postgres", "agreed, we're dropping the feature". Then they vanish into the scroll. Weeks later, nobody remembers *why*.

## What DecisionLog does

DecisionLog watches your channels, recognizes when a decision is being made, and turns it into a documented record — without anyone filling out a form.

1. **Detects** decision language in real time
2. **Drafts** a structured record (what, who, why, context)
3. **Asks** for one-click confirmation in the thread
4. **Stores** it in a searchable log mirrored to a Slack canvas
5. **Answers** later questions like *"why did we move the launch?"*

---

## How it works

```
Slack channel  ──▶  Event listener  ──▶  Decision detector  ──▶  Drafter
(conversation)      (Events API)         (Slack AI / LLM)        (builds card)
                                                                    │ context
                                                                    ▼
                                                            MCP server
                                                         (Jira · Drive · RTS)
                                                                    │
                                                                    ▼
Search agent  ◀──  Decision store  ◀──  Approval card  ◀───────────┘
("why did       (DB + Slack canvas)    (one-click confirm)
 we…?")
```

---

## Tech stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI (Python) |
| Agent framework | Slack Bolt for Python |
| Detection | Google Gemini (Gemini API) |
| Context enrichment | Slack MCP server + Real-Time Search API |
| Storage | Postgres + Slack canvas |
| Search | Embeddings + LLM |

Uses all three eligible Slack technologies: **Slack AI capabilities**, **MCP server integration**, and the **Real-Time Search API**.

---

## Getting started

### Prerequisites

- Python 3.10+
- A Slack developer sandbox workspace
- A Google Gemini API key

### Setup

```bash
git clone https://github.com/<your-team>/decisionlog.git
cd decisionlog
python -m venv venv
# On Windows: venv\Scripts\activate
# On macOS/Linux: source venv/bin/activate
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your tokens
uvicorn main:app --reload
```

### Environment variables

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_APP_TOKEN=xapp-...
GEMINI_API_KEY=AIzaSy...
DATABASE_URL=postgres://...
```

---

## Usage

- Invite the agent to any channel: `/invite @DecisionLog`
- Talk normally — when a decision is detected, DecisionLog posts a draft card
- Click **Confirm** to log it, or **Dismiss** to ignore
- Ask the agent anything: `@DecisionLog why did we choose Postgres?`

---

## Roadmap

- [x] Real-time decision detection
- [x] One-click approval card
- [x] Searchable decision store + Slack canvas
- [ ] Jira / Google Drive context enrichment
- [ ] Weekly decision digest
- [ ] Decision analytics (how many, by whom, reversal rate)

---

## Team

Built by a two-person team for the Slack Agent Builder Challenge.

## License

MIT
