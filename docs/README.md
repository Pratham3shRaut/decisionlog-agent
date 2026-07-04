# DecisionLog — Task Docs

One doc per completed engineering task, newest work building on older.

| # | Task | Status |
|---|---|---|
| [00](00-detection-hardening.md) | Decision-detection hardening (context + prompt rules + retry bugfix) | ✅ 13/14 eval |
| [01](01-mcp-integration.md) | MCP server integration (related-discussion enrichment) | ✅ tested |
| [02](02-real-time-search-api.md) | Real-Time Search API (`assistant.search.context`) | ✅ tested |
| [03](03-semantic-search.md) | Embeddings-based semantic search for Q&A | ✅ 4/4 eval |

## Eligible-technology coverage (challenge requirement)

- **MCP server integration** — ✅ [doc 01](01-mcp-integration.md)
- **Real-Time Search API** — ✅ [doc 02](02-real-time-search-api.md)
- **Bolt SDK** — ✅ already the app's core (Bolt for Python, Socket Mode)

## One-time setup the team still owes

1. **User token** `SLACK_USER_TOKEN=xoxp-…` with `search:read.public` (enables MCP + RTS).
2. Scopes `channels:history` (+ private/im/mpim variants) for context fetching.
3. A **paid Gemini key** for the demo (free tier = 20 req/day).

## Eval scripts

- `python eval_detection.py` — detection precision/recall (rate-limit-paced).
- `python eval_semantic_search.py` — semantic ranking accuracy.
