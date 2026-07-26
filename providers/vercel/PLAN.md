# Vercel BotID shim — plan

A small Next.js app, deployed on Vercel, that runs the (invisible) Vercel BotID
challenge and reports a "solve" back to the main BotThisSite FastAPI app on Nest.

BotID is an invisible anti-bot powered by Kasada. There's no widget, no token,
no `siteverify` URL, and no Python SDK. The only server check is `checkBotId()`
from the `botid/server` npm package, which must run on Vercel. So it does **not**
fit the `CaptchaProvider` registry in `providers.py` like Turnstile/reCAPTCHA do.

## The thematic mapping

This site's premise is "solve the captcha, number go up". BotID has no user
"solve". The closest honest mapping:

> **success = BotID classifies the request as NOT a bot (`isBot === false`)**,
> i.e. you slipped past the invisible detector. That records a solve for
> slug `vercel-botid`.

## Why it can't live on Nest / can't be embedded cross-origin

- BotID's client script **only attaches its challenge headers to same-origin
  requests**. Its `fetch` wrapper bails (`return originalFetch(...)`) when the
  request is cross-origin, so a page on `bts.zzz.hackclub.app` calling a Vercel
  endpoint sends NO BotID headers and `checkBotId()` returns `isBot: true`
  forever. (Confirmed by the Vercel community thread "BotID cross domain -
  isBot always true".)
- The first-party `c.js` signal script is served by **proxy rewrites that only
  exist on the Vercel origin** (set up by `withBotId`). They don't exist on Nest.

Conclusion: the **challenge page itself must be served from Vercel**. The Nest
site links/redirects to it. (An iframe of the Vercel page technically works
because everything inside the frame is the Vercel origin, but framing headers +
third-party storage partitioning make it fragile — avoid for v1.)

## Architecture

```
 Nest (FastAPI)                         Vercel (this shim)
 ─────────────                          ──────────────────
 homepage "Solve Vercel BotID" link
        │  https://<shim>.vercel.app/challenge?name=Demo
        ▼
                                   challenge page (client)
                                   - initBotId() ran at startup
                                   - fetch POST /api/botid {name}
                                     (same-origin → BotID headers attached)
                                        │
                                        ▼
                                   /api/botid route (server)
                                   - checkBotId() → {isBot}
                                   - if !isBot:
                                        │  POST /captchas/record
                                        │  header: X-BotID-Secret
                                        ▼
 /captchas/record (internal)  ◀─────────┘
   - verify shared secret
   - record_solve(name, "vercel-botid")
   - 200
                                   - return {success: !isBot} to page
        ▲                               │
        └─ leaderboard shows the ───────┘
           vercel-botid column
```

## Components

### Vercel shim (this dir) — Next.js App Router
- `next.config.ts` — `withBotId(nextConfig)` to install proxy rewrites.
- `instrumentation-client.ts` — `initBotId({ protect: [{ path: '/api/botid', method: 'POST' }] })`.
- `app/challenge/page.tsx` — reads `?name=`, POSTs to `/api/botid`, shows success/fail.
- `app/api/botid/route.ts` — `checkBotId()`; on human, POST solve to FastAPI; returns `{success}`.
- env: `FASTAPI_BASE_URL`, `BOTID_SHARED_SECRET`.

### FastAPI side (main app) — to do after the shim
1. Refactor: `record_solve()` already exists in `api/captchas.py` — reuse it.
2. New internal route `POST /captchas/record` guarded by `X-BotID-Secret`
   header (compared against `BOTID_SHARED_SECRET` env). Body `{name}`. Calls
   `record_solve(session, clean_data(name), "vercel-botid")`. Returns `{success: true}`.
3. `providers.py`: add a `vercel-botid` provider entry with
   `accepting=False` (no normal widget/verify flow — it has no site/secret key
   in the usual sense) and `listed=True` so it shows on the leaderboard.
   Because `accepting=False`, the normal `/captchas/{slug}` challenge + verify
   routes 404 it (correct — its flow lives on Vercel), but the leaderboard
   column still renders.
4. Homepage: add a special-cased "Solve Vercel BotID" link pointing at the
   Vercel shim URL (`<shim>/challenge?name=...`) instead of `/captchas/{slug}`.
   Needs a `VERCEL_BOTID_URL` env or hardcoded const.

## Caveats / risks
- **Plan/cost**: Basic mode is free; Deep Analysis is Pro plan + $1/1000
  `checkBotId()` calls. Start with Basic.
- **False positives**: VPN / datacenter IP / Linux / script-blocking users get
  flagged as bots (so they "fail" the solve). On-brand for this site, but noted.
- **Local dev**: `checkBotId()` always returns `isBot: false` locally, so the
  happy path can't really be tested until deployed to Vercel. Use
  `developmentOptions: { bypass: 'BAD-BOT' }` to exercise the fail path locally.
- **Testing in prod**: `curl`/headless hits get blocked outright; you must make
  a real-browser `fetch` from the challenge page.
- **Name trust**: `name` comes from the URL, so the FastAPI record endpoint must
  `clean_data()` it just like the existing verify route does.

## Status
- [x] Plan
- [ ] Vercel shim scaffold (in progress)
- [ ] FastAPI `/captchas/record` + provider entry + homepage link
- [ ] Deploy to Vercel, enable BotID in dashboard, end-to-end test
