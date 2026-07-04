"""
MCP client for DecisionLog: spawns mcp_server.py as a stdio subprocess and
calls its search_slack_messages tool to find related past discussions when
a decision is being drafted (context enrichment step in the architecture).
"""
import sys
import logging
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("decisionlog.mcp_client")

_server_params = StdioServerParameters(
    command=sys.executable,
    args=["mcp_server.py"],
)


async def search_related_discussions(query: str, count: int = 5) -> str:
    """
    Launches the MCP Slack-search server, calls search_slack_messages, and
    returns the formatted result. Each call spins up a fresh subprocess;
    fine for the drafting-time call volume this is used at.
    """
    try:
        async with AsyncExitStack() as stack:
            read, write = await stack.enter_async_context(stdio_client(_server_params))
            session = await stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            result = await session.call_tool(
                "search_slack_messages", arguments={"query": query, "count": count}
            )
            text_parts = [c.text for c in result.content if hasattr(c, "text")]
            return "\n".join(text_parts) if text_parts else "No related past discussions found."
    except Exception as e:
        logger.warning(f"MCP search_related_discussions failed: {e}")
        return "No related past discussions found."
