import { initBotId } from "botid/client/core";

// Runs before the app hydrates. Declares which same-origin requests BotID should
// attach challenge headers to. The path here MUST match the route that calls
// checkBotId() on the server, or checkBotId() will see no headers and report a
// bot.
initBotId({
  protect: [
    {
      path: "/api/botid",
      method: "POST",
    },
  ],
});
