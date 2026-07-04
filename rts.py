"""
Slack Real-Time Search (RTS) API integration.

Wraps the `assistant.search.context` Web API method, which surfaces fresh,
permission-aware, in-workspace context (messages/users/channels/files) to the
agent at the moment it's needed. This is one of the challenge's eligible
technologies and is the idiomatic way to fetch "related past discussions" —
richer and more permission-aware than the raw search.messages fallback.

Auth: `assistant.search.context` accepts a user token (xoxp-) directly. With a
bot token it additionally requires an `action_token` extracted from the
triggering message/app_mention event, so we prefer the user token here.
Docs: https://docs.slack.dev/apis/web-api/real-time-search-api/
"""
import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("decisionlog.rts")

# User token (xoxp-) with search:read.public (+ optional private/mpim/im/files/users) scopes.
_user_token = os.environ.get("SLACK_USER_TOKEN")
_client = WebClient(token=_user_token) if _user_token else None


def rts_available() -> bool:
    """True if a user token is configured for RTS calls."""
    return _client is not None


def search_context(query: str, count: int = 5, channel_types=None) -> str:
    """
    Call assistant.search.context and return a formatted string of matching messages.

    Args:
        query: Free-text natural-language query.
        count: Max messages to include in the formatted result.
        channel_types: Which conversation types to search; defaults to public + private channels.

    Returns:
        Formatted string of related messages, or a clear reason string if unavailable/empty.
    """
    if _client is None:
        return "RTS unavailable: SLACK_USER_TOKEN is not configured."

    if channel_types is None:
        channel_types = ["public_channel", "private_channel"]

    try:
        response = _client.api_call(
            "assistant.search.context",
            json={"query": query, "channel_types": channel_types},
        )
    except SlackApiError as e:
        error_code = e.response.get("error", "unknown_error")
        if error_code == "missing_scope":
            return "RTS unavailable: the user token is missing a required search:read.* scope."
        if error_code in ("method_not_supported_for_channel_type", "not_allowed_token_type"):
            return f"RTS unavailable: {error_code}."
        return f"RTS search failed: {error_code}"
    except Exception as e:
        logger.warning(f"RTS search_context unexpected error: {e}")
        return "RTS search failed: unexpected error."

    messages = (response.get("results") or {}).get("messages") or []
    if not messages:
        return "No related past discussions found."

    lines = []
    for m in messages[:count]:
        author = m.get("author_name") or m.get("author_user_id") or "unknown"
        content = (m.get("content") or "").replace("\n", " ").strip()
        permalink = m.get("permalink", "")
        suffix = f" ({permalink})" if permalink else ""
        lines.append(f"- {author}: {content}{suffix}")

    return "\n".join(lines)
