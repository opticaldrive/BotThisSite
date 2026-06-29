import type { NextConfig } from "next";
import { withBotId } from "botid/next/config";

const nextConfig: NextConfig = {
  // nothing special — BotThisSite's real app lives on Nest. This Vercel
  // deployment exists only to run the BotID challenge + /api/botid check.
};

// withBotId installs the proxy rewrites that serve BotID's first-party `c.js`
// signal script from this origin (so ad-blockers can't fingerprint it). These
// rewrites only exist on Vercel — which is exactly why the challenge page has
// to be served from here and not from Nest.
export default withBotId(nextConfig);
