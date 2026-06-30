import pkg from "@slack/bolt";
import { config } from "./config.js";
import { registerMessageListener } from "./listeners/message.js";
import { registerAppMentionListener } from "./listeners/appMention.js";

const { App } = pkg;

// Socket Mode lets us receive Slack events over a WebSocket instead of
// exposing a public HTTPS endpoint — ideal for local dev. socketMode: true
// pairs with the appToken (xapp-...) to open that connection.
const app = new App({
  token: config.slackBotToken,
  signingSecret: config.slackSigningSecret,
  appToken: config.slackAppToken,
  socketMode: true,
});

registerMessageListener(app);
registerAppMentionListener(app);

async function start() {
  await app.start();
  console.log("⚡️ DecisionLog running");
}

async function shutdown(signal) {
  console.log(`\n${signal} received, shutting down DecisionLog...`);
  await app.stop();
  console.log("DecisionLog stopped. Goodbye 👋");
  process.exit(0);
}

process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));

start().catch((error) => {
  console.error("❌ Failed to start DecisionLog:", error);
  process.exit(1);
});
