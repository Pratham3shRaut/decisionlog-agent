# Task: MCP Server Integration

**Status:** ✅ Implemented and tested
**Eligible technology satisfied:** MCP (Model Context Protocol) server integration

## Goal

Add a Model Context Protocol server to DecisionLog so the agent can enrich a
drafted decision with **related past discussions from across the workspace** —
one of the Slack Agent Builder Challenge's three required technologies.

## What was built

| File | Role |
|---|---|
| [`mcp_server.py`](../mcp_server.py) | Standalone MCP server (official `mcp` SDK, **stdio** transport) exposing the `search_slack_messages` tool. |
| [`mcp_client.py`](../mcp_client.py) | MCP **client**: spawns the server as a subprocess, opens a session, calls the tool, returns results. |
| [`handlers/messages.py`](../handlers/messages.py) | On decision detection, calls `search_related_discussions(summary)` and adds a "🔎 Related past discussions" section to the approval card. |

## Flow

```
decision detected in messages.py
        │
        ▼
search_related_discussions(summary)      (mcp_client.py)
        │  spawns subprocess over stdio
        ▼
search_slack_messages tool               (mcp_server.py)
        │  delegates to →
        ▼
Real-Time Search API (assistant.search.context)  ── fallback ──▶ search.messages
        │
        ▼
formatted "related discussions" → added to the Block Kit card
```

## Design decisions

- **We built our own MCP server** rather than using a community one
  (`korotovsky/slack-mcp-server`), because that server authenticates via scraped
  browser session tokens (`xoxc`/`xoxd`) to bypass app scopes — inappropriate for
  a judged submission. Ours uses the app's sanctioned tokens under approved scopes.
- **stdio transport** keeps the server as a spawned subprocess — no extra ports,
  no separate deployment.
- The MCP tool **delegates to the Real-Time Search API** (see
  [`02-real-time-search-api.md`](02-real-time-search-api.md)) and only falls back
  to the classic `search.messages` endpoint if RTS is unavailable.

## Auth requirement

`search.messages` / RTS require a **user token** (`xoxp-`), not a bot token
(Slack returns `not_allowed_token_type` for bot tokens on `search.*`). Add to `.env`:

```
SLACK_USER_TOKEN=xoxp-...   # with search:read.public (+ optional search:read.* scopes)
```

If this token is absent, the feature **degrades gracefully**: no card block is
added, and nothing crashes.

## Testing performed

- ✅ `python -m py_compile` on all new/changed files.
- ✅ End-to-end chain test: `mcp_client.search_related_discussions(...)` spawns the
  server, calls the tool, and returns a clean result. Verified the graceful path
  when `SLACK_USER_TOKEN` is unset (returns `"Search unavailable: SLACK_USER_TOKEN is not configured."`).
- ✅ Live reachability test confirmed `assistant.search.context` is the correct
  method name and request shape (Slack responded with real scope negotiation,
  not `unknown_method`).

## Follow-up needed by the team

1. Create a **user OAuth token** with `search:read.public` scope in the Slack app
   settings (OAuth & Permissions → User Token Scopes) and set `SLACK_USER_TOKEN`.
2. Reinstall the app to the workspace to apply the new scope.
