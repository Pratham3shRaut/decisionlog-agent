import dotenv from "dotenv";

dotenv.config();

// Every variable the app needs at startup. Fail fast with a clear message
// rather than letting Bolt throw a cryptic error deep in its init code.
const REQUIRED_VARS = ["SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET", "SLACK_APP_TOKEN"];

function loadConfig() {
  const missing = REQUIRED_VARS.filter((key) => !process.env[key]);

  if (missing.length > 0) {
    console.error("❌ Missing required environment variable(s): " + missing.join(", "));
    console.error("   Copy .env.example to .env and fill in the values, then try again.");
    process.exit(1);
  }

  return {
    slackBotToken: process.env.SLACK_BOT_TOKEN,
    slackSigningSecret: process.env.SLACK_SIGNING_SECRET,
    slackAppToken: process.env.SLACK_APP_TOKEN,
  };
}

export const config = loadConfig();
