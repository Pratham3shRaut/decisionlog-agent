import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.aiohttp import AsyncSocketModeHandler

from db import init_db
from handlers import register_handlers

import logging

# Load environment variables
load_dotenv()

# Check logging flag (defaults to True)
logging_enabled = os.environ.get("LOGGING_ENABLED", "true").lower() in ("true", "1", "yes")

# Configure logging
if logging_enabled:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("app.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
else:
    # When disabled, only output error and critical messages to standard output
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )

logger = logging.getLogger("decisionlog")

# Initialize database tables
try:
    logger.info("Initializing database tables...")
    init_db()
    logger.info("Database tables initialized successfully.")
except Exception as db_err:
    logger.error(f"Error initializing database: {db_err}")

# Initialize Slack Bolt App (Async Mode)
bolt_app = AsyncApp(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Register all Slack event and action listeners
register_handlers(bolt_app)

socket_handler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global socket_handler
    print("Starting Slack Bolt Socket Mode client...")
    
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        print("WARNING: SLACK_APP_TOKEN is not set. Slack Socket Mode will not start.")
    else:
        # Create Socket Mode handler
        socket_handler = AsyncSocketModeHandler(
            app=bolt_app,
            app_token=app_token
        )
        # Start socket mode asynchronously in the background so it doesn't block FastAPI
        asyncio.create_task(socket_handler.start_async())
        print("Slack Bolt Socket Mode client is running in the background.")
        
    yield
    
    # Graceful shutdown
    if socket_handler:
        print("Stopping Slack Bolt Socket Mode client...")
        await socket_handler.close()
        print("Slack Bolt Socket Mode client stopped.")

# Initialize FastAPI App with Lifespan handler
app = FastAPI(
    title="DecisionLog API",
    description="FastAPI Backend & Slack Agent for DecisionLog",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
def health_check():
    """Health check endpoint to verify backend service status."""
    return {
        "status": "healthy",
        "service": "DecisionLog Slack Agent",
        "database_connected": os.environ.get("DATABASE_URL") is not None
    }

# Force reload to apply new Slack Socket Mode configuration and scopes
