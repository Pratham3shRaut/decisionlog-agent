// Handles "app_mention" events (someone @-mentions the bot). Used here as a
// simple end-to-end wiring check: mention the bot, get a reply.
export function registerAppMentionListener(app) {
  app.event("app_mention", async ({ event, say, logger }) => {
    logger.info(`[app_mention] channel=${event.channel} user=${event.user}`);

    await say({
      text: "DecisionLog is listening 👀",
      thread_ts: event.thread_ts || event.ts,
    });
  });
}
