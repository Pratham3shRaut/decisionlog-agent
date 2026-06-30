// Handles the Slack "message" event. Day 1 scope: log non-bot messages so we
// can confirm events are flowing — no detection or storage yet.
export function registerMessageListener(app) {
  app.message(async ({ message, logger }) => {
    // Slack sends "subtype" for things like message_changed, message_deleted,
    // channel_join, etc. Skip those so we only log genuine user messages and
    // don't risk reacting to our own edits/echoes.
    if (message.subtype || message.bot_id) {
      return;
    }

    const { channel, user, ts, text } = message;

    logger.info(
      `[message] channel=${channel} user=${user} ts=${ts} text="${text}"`
    );
  });
}
