import json
import logging
from slack_bolt.async_app import AsyncApp
from db import SessionLocal, LoggedDecision

logger = logging.getLogger("decisionlog.actions")

def register_action_handlers(app: AsyncApp):
    @app.action("confirm_decision")
    async def handle_confirm(ack, body, client):
        logger.info("Received 'confirm_decision' action trigger")
        await ack()
        
        # Get the payload and value
        action = body.get("actions", [{}])[0]
        value_str = action.get("value")
        
        if not value_str:
            logger.warning("No value string found in action payload")
            return
            
        try:
            data = json.loads(value_str)
            summary = data.get("summary")
            rationale = data.get("rationale")
            decision_maker = data.get("decision_maker")
            channel_id = data.get("channel_id")
            thread_ts = data.get("thread_ts")
            
            logger.info(f"Confirm payload parsed: summary='{summary}', maker='{decision_maker}', channel='{channel_id}'")
            
            # Save to PostgreSQL using SQLAlchemy
            db = SessionLocal()
            try:
                logger.info("Connecting to DB and committing decision record...")
                new_decision = LoggedDecision(
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    summary=summary,
                    rationale=rationale,
                    decision_maker=decision_maker
                )
                db.add(new_decision)
                db.commit()
                db.refresh(new_decision)
                logger.info(f"Successfully logged decision to DB: ID {new_decision.id}")
            except Exception as db_err:
                db.rollback()
                logger.error(f"Database error saving decision: {db_err}", exc_info=True)
                raise db_err
            finally:
                db.close()
                
            # Update the original Slack card to show it's successfully logged
            response_blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "✅ Decision Logged",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"This decision has been saved to the permanent archive.\n\n"
                               f"*What:* {summary}\n"
                               f"*Why:* {rationale}\n"
                               f"*Who:* {decision_maker}"
                    }
                }
            ]
            
            container = body.get("container", {})
            container_channel_id = container.get("channel_id")
            message_ts = container.get("message_ts")
            
            logger.info(f"Updating original Block Kit card in Slack channel '{container_channel_id}' ts '{message_ts}'...")
            await client.chat_update(
                channel=container_channel_id,
                ts=message_ts,
                blocks=response_blocks,
                text="Decision Logged"
            )
            logger.info("Successfully updated Block Kit card to 'Decision Logged'.")
            
        except Exception as e:
            logger.error(f"Error handling confirm action: {e}", exc_info=True)

    @app.action("dismiss_decision")
    async def handle_dismiss(ack, body, client):
        logger.info("Received 'dismiss_decision' action trigger")
        await ack()
        
        try:
            # Update the original Slack card to show it's dismissed
            response_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "❌ _This decision draft was dismissed._"
                    }
                }
            ]
            
            container = body.get("container", {})
            container_channel_id = container.get("channel_id")
            message_ts = container.get("message_ts")
            
            logger.info(f"Dismissing original Block Kit card in channel '{container_channel_id}' ts '{message_ts}'...")
            await client.chat_update(
                channel=container_channel_id,
                ts=message_ts,
                blocks=response_blocks,
                text="Decision Draft Dismissed"
            )
            logger.info("Successfully updated Block Kit card to 'Dismissed'.")
        except Exception as e:
            logger.error(f"Error handling dismiss action: {e}", exc_info=True)
