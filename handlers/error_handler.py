import logging
import traceback

logger = logging.getLogger("decisionlog.errors")

async def report_error_to_slack(client, error: Exception, original_channel: str, thread_ts: str, original_message: str):
    """
    Handles errors by posting the detailed technical traceback and context ONLY to #say-chakli.
    No messages are posted to the original/observer channel.
    """
    logger.error(f"Reporting exception to Slack: {error}", exc_info=True)
    
    err_str = str(error)
    # Check if it looks like a rate limit error (429)
    if any(term in err_str for term in ("429", "ResourceExhausted", "Too Many Requests", "Quota exceeded")):
        friendly_error = "Rate limit exceeded (the Gemini API is temporarily busy)."
    else:
        friendly_error = f"Technical issue ({type(error).__name__})."

    # 1. Construct detailed diagnostic layout
    trace_str = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    # Truncate traceback if it's too long for Slack
    if len(trace_str) > 2500:
        trace_str = trace_str[-2500:]

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🚨 Technical Error Logged",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"I received a message in <#{original_channel}> but was unable to respond due to: *{friendly_error}*\n\n"
                       f"*Error:* `{type(error).__name__}: {str(error)}`\n"
                       f"*Thread TS:* `{thread_ts}`"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Original Message Text:*\n```\n{original_message}\n```"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Traceback:*\n```\n{trace_str}\n```"
            }
        }
    ]

    # 2. Post the detailed technical message to #say-chakli directly using name
    try:
        logger.info("Posting detailed diagnostics directly to #say-chakli...")
        await client.chat_postMessage(
            channel="#say-chakli",
            blocks=blocks,
            text=f"Technical Error: {type(error).__name__}"
        )
        logger.info("Successfully logged diagnostics to #say-chakli.")
    except Exception as post_err:
        logger.error(f"Failed to post detailed diagnostics to #say-chakli: {post_err}")
