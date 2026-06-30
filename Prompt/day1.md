You are helping me build "DecisionLog", a Slack agent for the Slack Agent
Builder Challenge. I'm working on Day 1: a working Bolt for JavaScript skeleton
that connects to Slack, subscribes to message events, and logs them.

Build me a minimal but production-clean starting point. Requirements:

PROJECT SETUP
- Node.js 18+, Slack Bolt for JavaScript (@slack/bolt), using Socket Mode for
  local dev (so I don't need a public HTTPS endpoint yet).
- ES modules (type: "module" in package.json).
- Use dotenv for config. Provide a .env.example listing every variable.
- Give me package.json with a "dev" script that runs the app with auto-reload
  (nodemon or node --watch).

FUNCTIONALITY (Day 1 scope only — do NOT build detection or storage yet)
- Initialize the Bolt app with SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, and
  SLACK_APP_TOKEN.
- Listen to the "message" event in channels the bot is a member of.
- For each non-bot message, log to console: channel ID, user ID, timestamp,
  and the message text. Ignore the bot's own messages and message subtypes
  like edits/joins to avoid loops.
- Add a simple "app_mention" handler that replies "DecisionLog is listening 👀"
  so I can confirm the agent is wired up end to end.
- Include graceful startup/shutdown logging ("⚡️ DecisionLog running").

CODE QUALITY
- Clear file structure: app.js (entry), config.js (env loading + validation
  that fails fast with a helpful message if a var is missing), and a
  listeners/ folder splitting the message and mention handlers.
- Comment the parts that are Slack-specific so a teammate who's new to Bolt
  can follow it.
- No detection logic, no database, no LLM calls yet — keep it to the skeleton.

DELIVER
- All files with their full contents and paths.
- A short "Slack app config checklist" telling me exactly which scopes
  (e.g. channels:history, app_mentions:read, chat:write) and event
  subscriptions I need to enable in the Slack app dashboard, and where to find
  each of the three tokens.
- The exact commands to install and run it.

Ask me any clarifying question only if something would block you; otherwise
build it.