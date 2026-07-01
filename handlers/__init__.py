from slack_bolt.async_app import AsyncApp
from handlers.messages import register_message_handlers
from handlers.actions import register_action_handlers
from handlers.mentions import register_mention_handlers

def register_handlers(app: AsyncApp):
    """Register all Slack events and actions to the Slack App instance."""
    register_message_handlers(app)
    register_action_handlers(app)
    register_mention_handlers(app)
