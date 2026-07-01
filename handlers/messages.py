import json
import logging
from slack_bolt.async_app import AsyncApp
from gemini import detect_decision

logger = logging.getLogger("decisionlog.messages")

def register_message_handlers(app: AsyncApp):
    @app.event("message")
    async def handle_message_events(event, say, client):
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
        
        logger.info(f"Processing message from user '{user}' in channel '{channel}': '{text}'")
        
        # Check if the message is in a thread (we can handle thread messages too)
        thread_ts = event.get("thread_ts", ts)
        
        # Detect decision
        logger.info("Calling Gemini for decision detection...")
        try:
            analysis = detect_decision(text)
        except Exception as e:
            logger.error(f"Failed to detect decision using Gemini: {e}", exc_info=True)
            return
            
        logger.info(f"Gemini detection analysis: is_decision={analysis.is_decision}, summary='{analysis.summary}', rationale='{analysis.rationale}', maker='{analysis.decision_maker}'")
        
        if analysis.is_decision:
            summary = analysis.summary or "No summary provided"
            rationale = analysis.rationale or "No rationale provided"
            decision_maker = analysis.decision_maker or "Team"
            
            # Map user ID to human readable format if decision maker looks like a Slack user ID
            if decision_maker.startswith("<@") and decision_maker.endswith(">"):
                # Use as-is, Slack will render it
                user_mention = decision_maker
            elif decision_maker.lower() == "team":
                user_mention = "Collective Team"
            else:
                # Default to mention the sender of the message
                user_mention = f"<@{user}>"

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
                {
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
                }
            ]
            
            try:
                # Post the card in the thread of the message
                logger.info(f"Posting decision draft card to channel {channel}, thread {thread_ts}...")
                await say(
                    blocks=blocks,
                    text=f"Decision Drafted: {summary}",
                    thread_ts=thread_ts
                )
                logger.info("Successfully posted decision draft card to Slack.")
            except Exception as e:
                logger.error(f"Error posting decision card to Slack: {e}", exc_info=True)
        else:
            logger.info("Message was not identified as a decision. Ignoring.")
