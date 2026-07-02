import re
import asyncio
import logging
from slack_bolt.async_app import AsyncApp
from db import SessionLocal, LoggedDecision
from gemini import answer_query

logger = logging.getLogger("decisionlog.mentions")

async def process_mention_async(event, say, client):
    text = event.get("text", "")
    channel_id = event.get("channel")
    thread_ts = event.get("thread_ts", event.get("ts"))
    
    try:
        # Clean the query (remove the bot user mention)
        # E.g. <@U12345678> why did we choose postgres? -> why did we choose postgres?
        query = re.sub(r"<@[A-Z0-9]+>", "", text).strip()
        
        if not query:
            try:
                await say(
                    text="Hi there! Mention me and ask a question, e.g. `@DecisionLog why did we decide to deploy on Friday?`",
                    thread_ts=thread_ts
                )
            except Exception as e:
                logger.error(f"Error replying to empty app mention: {e}")
            return

        # Fetch recent logged decisions for context from this channel
        db = SessionLocal()
        try:
            # Fetch up to 50 recent decisions for this channel to build context
            decisions = (
                db.query(LoggedDecision)
                .filter(LoggedDecision.channel_id == channel_id)
                .order_by(LoggedDecision.created_at.desc())
                .limit(50)
                .all()
            )
            
            # If no decisions in this channel, maybe check globally
            if not decisions:
                decisions = (
                    db.query(LoggedDecision)
                    .order_by(LoggedDecision.created_at.desc())
                    .limit(50)
                    .all()
                )
                
            # Serialize for Gemini
            logs = []
            for d in decisions:
                logs.append({
                    "summary": d.summary,
                    "rationale": d.rationale,
                    "decision_maker": d.decision_maker,
                    "created_at": d.created_at.strftime("%Y-%m-%d %H:%M:%S")
                })
        except Exception as db_err:
            logger.error(f"Error fetching decisions for Q&A: {db_err}")
            logs = []
        finally:
            db.close()
            
        # Get response from Gemini, passing the current query date for relative date matching
        from datetime import datetime
        try:
            mention_time = datetime.fromtimestamp(float(event.get("ts", 0)))
            current_date_str = mention_time.strftime("%A, %B %d, %Y")
        except Exception:
            current_date_str = datetime.now().strftime("%A, %B %d, %Y")
            
        response_text = answer_query(query, logs, current_date=current_date_str)
        
        await say(
            text=response_text,
            thread_ts=thread_ts
        )
    except Exception as e:
        logger.error(f"Error in process_mention_async: {e}", exc_info=True)
        from handlers.error_handler import report_error_to_slack
        await report_error_to_slack(client, e, channel_id, thread_ts, text)

def register_mention_handlers(app: AsyncApp):
    @app.event("app_mention")
    async def handle_mentions(event, say, client):
        # Dispatch the actual work to a background task so we can instantly acknowledge the event to Slack.
        # This prevents Slack's 3-second timeout from triggering duplicate retries.
        asyncio.create_task(process_mention_async(event, say, client))
