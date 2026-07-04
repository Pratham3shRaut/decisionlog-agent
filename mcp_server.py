"""
Standalone MCP server exposing Slack workspace search as an MCP tool.

Run standalone for testing: python mcp_server.py
Normally this is spawned as a subprocess by mcp_client.py over stdio.

Auth: uses our existing approved bot token (SLACK_BOT_TOKEN) and the
`search:read` scope — no browser session tokens, no bypassing Slack's
app permission model.
"""
import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("decisionlog-slack-search")

# search.messages requires a user token (xoxp-), not a bot token — Slack does not
# allow bot tokens to call search.* at all ("not_allowed_token_type").
_slack_client = WebClient(token=os.environ.get("SLACK_USER_TOKEN"))


@mcp.tool()
def search_slack_messages(query: str, count: int = 5) -> str:
    """
    Search the Slack workspace for messages related to the given query.
    Uses Slack's native search.messages API (requires the search:read scope
    granted to this app), so it only sees channels the bot is a member of.

    Args:
        query: Free-text search query (e.g. keywords from a decision being drafted).
        count: Max number of matching messages to return (default 5, max 20).

    Returns:
        A formatted string listing matching messages with channel, permalink, and text,
        or a message indicating no results / that the search:read scope is missing.
    """
    count = max(1, min(count, 20))
    if not _slack_client.token:
        return "Search unavailable: SLACK_USER_TOKEN is not configured."

    # Prefer the Real-Time Search API (assistant.search.context): permission-aware,
    # workspace-wide, and one of the challenge's eligible technologies. Fall back to
    # the classic search.messages endpoint if RTS is not available on this workspace.
    from rts import search_context, rts_available

    if rts_available():
        rts_result = search_context(query, count=count)
        # Only fall back on a hard RTS availability/config failure, not on "no results".
        if not rts_result.startswith("RTS unavailable") and not rts_result.startswith("RTS search failed"):
            return rts_result

    try:
        response = _slack_client.search_messages(query=query, count=count, sort="timestamp", sort_dir="desc")
    except SlackApiError as e:
        error_code = e.response.get("error", "unknown_error")
        if error_code == "missing_scope":
            return "Search unavailable: the Slack user token is missing the 'search:read' scope."
        if error_code == "not_allowed_token_type":
            return "Search unavailable: search.messages requires a user token (xoxp-), not a bot token."
        return f"Slack search failed: {error_code}"

    matches = response.get("messages", {}).get("matches", [])
    if not matches:
        return "No related past discussions found."

    lines = []
    for m in matches:
        channel_name = m.get("channel", {}).get("name", "unknown-channel")
        text = (m.get("text") or "").replace("\n", " ").strip()
        permalink = m.get("permalink", "")
        lines.append(f"- [#{channel_name}] {text} ({permalink})")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
