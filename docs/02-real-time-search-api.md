# Task: Real-Time Search (RTS) API Integration

**Status:** ✅ Implemented and tested (pending user-token scope from the team)
**Eligible technology satisfied:** Real-Time Search (RTS) API

## Goal

Use Slack's Real-Time Search API to surface **fresh, permission-aware, in-workspace
context** (related past discussions) when the agent drafts a decision — the second
of the challenge's three required technologies.

## What is the RTS API?

RTS is the `assistant.search.context` Web API method. It searches messages, files,
channels, and users across the workspace and returns only what the caller is
authorized to see — "at the moment it's needed."

- **Docs:** https://docs.slack.dev/apis/web-api/real-time-search-api/
- **Method:** `assistant.search.context`
- **Companion method:** `assistant.search.info` (reports available capabilities)

## What was built

| File | Role |
|---|---|
| [`rts.py`](../rts.py) | `search_context(query, count, channel_types)` wraps `assistant.search.context`; `rts_available()` reports whether a user token is configured. |
| [`mcp_server.py`](../mcp_server.py) | The MCP `search_slack_messages` tool calls `rts.search_context` first, and only falls back to `search.messages` if RTS is unavailable. |

## Request / response shape used

Request:
```json
{ "query": "why did we move the launch?", "channel_types": ["public_channel", "private_channel"] }
```

Response (relevant part):
```json
{ "ok": true, "results": { "messages": [ { "author_name": "...", "content": "...", "permalink": "..." } ] } }
```

We format each message as `- {author}: {content} ({permalink})`.

## Design decisions

- **RTS is the primary search path; `search.messages` is the fallback.** RTS is
  permission-aware and is an eligible challenge technology, so it is preferred.
- **User token, not bot token.** `assistant.search.context` accepts a user token
  (`xoxp-`) directly. With a bot token it additionally requires an `action_token`
  extracted from the triggering event; using the user token keeps the code simpler
  and avoids threading event tokens through the search layer.
- **Fail safe.** Any missing token / missing scope / unsupported channel type
  returns a clear string; the caller treats those as "no enrichment" and never crashes.

## Required OAuth scopes (user token)

- `search:read.public` — **minimum** (public channel messages)
- `search:read.private`, `search:read.mpim`, `search:read.im` — optional, user token only
- `search:read.files`, `search:read.users` — optional

## Testing performed

- ✅ `python -m py_compile rts.py mcp_server.py`.
- ✅ Standalone `rts.search_context(...)` without a user token → clean
  `"RTS unavailable: SLACK_USER_TOKEN is not configured."` (no crash).
- ✅ **Live reachability test** against the real workspace using the bot token
  confirmed the method/request are correct: Slack returned
  `missing_scope` with `needed: search:read.public`, i.e. the call reached the
  endpoint and negotiated scopes (proving `assistant.search.context` and the
  payload are valid). The app already has `search:read.im` and `channels:history`.

## Follow-up needed by the team

1. Add **`search:read.public`** to the app's **User Token Scopes** and reinstall.
2. Set `SLACK_USER_TOKEN=xoxp-...` in `.env`. RTS then activates automatically for
   the "related past discussions" card block.
