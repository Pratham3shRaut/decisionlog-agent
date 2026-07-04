import json
import logging
import asyncio
from slack_bolt.async_app import AsyncApp
from gemini import detect_decision
from mcp_client import search_related_discussions

logger = logging.getLogger("decisionlog.messages")

async def process_message_async(event, say, client):
    text = event.get("text")
    channel = event.get("channel")
    ts = event.get("ts")
    user = event.get("user")
    thread_ts = event.get("thread_ts", ts)
    
    try:
        # Get sender's real name or display name using client.users_info (requires users:read scope)
        sender_name = f"<@{user}>"
        try:
            logger.info(f"Fetching user profile for {user}...")
            user_info = await client.users_info(user=user)
            user_profile = user_info.get("user", {})
            sender_name = user_profile.get("real_name") or user_profile.get("name") or sender_name
            logger.info(f"Resolved user ID '{user}' to name '{sender_name}'")
        except Exception as u_err:
            logger.warning(f"Could not fetch user profile (scope 'users:read' might be missing): {u_err}")
            
        # Convert message timestamp to human-readable date for relative date resolution
        from datetime import datetime
        try:
            msg_time = datetime.fromtimestamp(float(ts))
            current_date_str = msg_time.strftime("%A, %B %d, %Y")
        except Exception:
            current_date_str = datetime.now().strftime("%A, %B %d, %Y")
            
        logger.info(f"Processing message from user '{sender_name}' ({user}) in channel '{channel}' at '{current_date_str}': '{text}'")

        # Fetch recent preceding messages in the same channel/thread to give the detector conversational context.
        # Without this, multi-message decisions (proposal in one message, agreement in another) are invisible.
        context_str = None
        try:
            if event.get("thread_ts"):
                history = await client.conversations_replies(channel=channel, ts=thread_ts, limit=10)
            else:
                history = await client.conversations_history(channel=channel, latest=ts, limit=6, inclusive=False)
            history_messages = history.get("messages", [])
            # conversations_history returns newest-first; conversations_replies returns oldest-first
            if not event.get("thread_ts"):
                history_messages = list(reversed(history_messages))
            context_lines = []
            for m in history_messages:
                if m.get("ts") == ts:
                    continue
                m_text = m.get("text")
                if not m_text:
                    continue
                context_lines.append(f"<@{m.get('user', 'unknown')}>: {m_text}")
            if context_lines:
                context_str = "\n".join(context_lines[-6:])
                logger.info(f"Built conversation context ({len(context_lines)} messages) for decision detection.")
        except Exception as ctx_err:
            logger.warning(f"Could not fetch conversation context: {ctx_err}")

        # Detect decision
        logger.info("Calling Gemini for decision detection...")
        analysis = detect_decision(text, context=context_str, sender_name=sender_name, current_date=current_date_str)
            
        logger.info(f"Gemini detection analysis: is_decision={analysis.is_decision}, summary='{analysis.summary}', rationale='{analysis.rationale}', maker='{analysis.decision_maker}'")
        
        if analysis.is_decision:
            summary = analysis.summary or "No summary provided"
            rationale = analysis.rationale or "No rationale provided"
            decision_maker = analysis.decision_maker or "Team"
            
            # Map user ID or name to human readable format
            if decision_maker.startswith("<@") and decision_maker.endswith(">"):
                # Use as-is, Slack will render it
                user_mention = decision_maker
            elif decision_maker.lower() in ("team", "collective team"):
                user_mention = "Collective Team"
            elif sender_name and (decision_maker.lower() in sender_name.lower() or sender_name.lower() in decision_maker.lower()):
                # If it matches the sender's resolved name, render it as a Slack mention
                user_mention = f"<@{user}>"
            else:
                # Custom name extracted by Gemini
                user_mention = decision_maker

            # Enrich with related past discussions across the workspace via the MCP search server.
            # This is the "context enrichment" step in the architecture: a decision draft should
            # surface prior conversations on the same topic, not just the triggering message.
            related_discussions = None
            try:
                related_discussions = await search_related_discussions(summary, count=3)
                if related_discussions and related_discussions != "No related past discussions found.":
                    logger.info("Found related past discussions via MCP search.")
                else:
                    related_discussions = None
            except Exception as mcp_err:
                logger.warning(f"MCP related-discussion search failed: {mcp_err}")

            # Serialize decision data to include in the button action value (stateless)
            action_value = json.dumps({
                "summary": summary,
                "rationale": rationale,
                "decision_maker": user_mention,
                "channel_id": channel,
                "thread_ts": thread_ts
            })
            
            # Construct interactive Block Kit card
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📝 Decision Drafted",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"I detected a decision in this channel. Would you like to log it?\n\n"
                               f"*What:* {summary}\n"
                               f"*Why:* {rationale}\n"
                               f"*Who:* {user_mention}"
                     }
                },
            ]

            if related_discussions:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*🔎 Related past discussions:*\n{related_discussions}"
                    }
                })

            blocks.append({
                    "type": "actions",
                    "block_id": f"decision_actions_{ts}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Confirm & Log",
                                "emoji": True
                            },
                            "style": "primary",
                            "action_id": "confirm_decision",
                            "value": action_value
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "❌ Dismiss",
                                "emoji": True
                            },
                            "style": "danger",
                            "action_id": "dismiss_decision",
                            "value": "dismissed"
                        }
                    ]
                })

            # Post the card in the thread of the message
            logger.info(f"Posting decision draft card to channel {channel}, thread {thread_ts}...")
            await say(
                blocks=blocks,
                text=f"Decision Drafted: {summary}",
                thread_ts=thread_ts
            )
            logger.info("Successfully posted decision draft card to Slack.")
        else:
            logger.info("Message was not identified as a decision. Ignoring.")
    except Exception as e:
        logger.error(f"Error in process_message_async: {e}", exc_info=True)
        from handlers.error_handler import report_error_to_slack
        await report_error_to_slack(client, e, channel, thread_ts, text)

def register_message_handlers(app: AsyncApp):
    @app.event("message")
    async def handle_message_events(event, say, client, context):
        text = event.get("text")
        channel = event.get("channel")
        ts = event.get("ts")
        user = event.get("user")
        bot_id = event.get("bot_id")
        
        # Log all incoming message events at debug level
        logger.debug(f"Received raw message event: text='{text}', user='{user}', bot_id='{bot_id}', channel='{channel}', ts='{ts}'")

        # Ignore bot messages or messages without text
        if bot_id:
            logger.debug(f"Ignoring message because it was posted by bot '{bot_id}'")
            return
        if not text:
            logger.debug("Ignoring message because it does not contain text")
            return

        # Ignore messages that mention this bot (these are handled by app_mention or are conversational queries)
        bot_user_id = context.get("bot_user_id")
        if bot_user_id and f"<@{bot_user_id}>" in text:
            logger.debug(f"Ignoring message because it mentions the bot '{bot_user_id}'")
            return

        # Dispatch candidate messages to process asynchronously in background.
        # This keeps the main Bolt listener highly responsive and acknowledges events to Slack immediately.
        asyncio.create_task(process_message_async(event, say, client))
