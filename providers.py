# Central registry of captcha providers.
#
# To add a new captcha provider you (ideally) only do TWO things:
#   1. Add a CaptchaProvider(...) entry to PROVIDERS below.
#   2. Put its SITE_KEY / SECRET_KEY in .env (names referenced below).
#
# That's it. The verify route, the challenge page, the homepage link and the
# leaderboard column all read from this registry automatically.
#
# Most modern captchas (Cloudflare Turnstile, reCAPTCHA v2, hCaptcha, ...) share
# the exact same shape: load a <script>, render a <div class="..." data-sitekey>
# widget, and verify by POSTing {secret, response} to a siteverify URL that
# returns JSON with a boolean "success". So the defaults below "just work" for
# those. For an odd one out, set template="challenges/your-custom.html".

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # make SITE_KEY/SECRET_KEY env vars available


@dataclass(frozen=True)
class CaptchaProvider:
    slug: str  # url-safe id, e.g. "cf-turnstile". also the SolveEvent.captcha_type
    name: str  # human label for the UI, e.g. "Cloudflare Turnstile"
    verify_url: str  # server-side siteverify endpoint
    script_url: str  # <script src> the widget needs
    widget_class: str  # css class the widget script looks for
    site_key_env: str  # name of the env var holding the public site key
    secret_key_env: str  # name of the env var holding the private secret key
    template: str = "challenges/generic.html"  # override for non-standard captchas
    # Two independent kill-switches. Neither touches the DB, so flipping either
    # back to True restores everything exactly as it was.
    accepting: bool = True  # accept NEW solves? False -> challenge page + verify
    # route 404, and the homepage "solve" links/dropdown hide it (no quota burn,
    # no token replay). Existing SolveCount/SolveEvent rows are untouched.
    listed: bool = True  # show on the leaderboard? False -> its column is hidden
    # AND its counts drop out of the grand/per-user totals (kept consistent).

    @property
    def site_key(self) -> str | None:
        return os.getenv(self.site_key_env)

    @property
    def secret_key(self) -> str | None:
        return os.getenv(self.secret_key_env)


# The one place to register captchas. Add a line, add env vars, done.
PROVIDERS: dict[str, CaptchaProvider] = {
    p.slug: p
    for p in [
        CaptchaProvider(
            slug="cf-turnstile",
            name="Cloudflare Turnstile",
            verify_url="https://challenges.cloudflare.com/turnstile/v0/siteverify",
            script_url="https://challenges.cloudflare.com/turnstile/v0/api.js",
            widget_class="cf-turnstile",
            site_key_env="CF_SITE_KEY",
            secret_key_env="CF_SECRET_KEY",
        ),
        CaptchaProvider(
            slug="recaptcha-v2",
            name="reCAPTCHA v2",
            verify_url="https://www.google.com/recaptcha/api/siteverify",
            script_url="https://www.google.com/recaptcha/api.js",
            widget_class="g-recaptcha",
            site_key_env="RECAPTCHA_V2_SITE_KEY",
            secret_key_env="RECAPTCHA_V2_SECRET_KEY",
            # TEMPORARILY not accepting new solves: hitting the 10k/mo siteverify
            # limit + tokens were replayable on fail-open. Leaderboard stays up
            # (listed=True). To also pull it off the leaderboard, set listed=False.
            accepting=False,
        ),
        # --- add more captchas here, e.g. hCaptcha: ---
        # CaptchaProvider(
        #     slug="hcaptcha",
        #     name="hCaptcha",
        #     verify_url="https://api.hcaptcha.com/siteverify",
        #     script_url="https://js.hcaptcha.com/1/api.js",
        #     widget_class="h-captcha",
        #     site_key_env="HCAPTCHA_SITE_KEY",
        #     secret_key_env="HCAPTCHA_SECRET_KEY",
        # ),
    ]
}


def accepting_providers() -> list[CaptchaProvider]:
    """Providers that still accept solves -> homepage 'solve' links/dropdown."""
    return [p for p in PROVIDERS.values() if p.accepting]


def listed_providers() -> list[CaptchaProvider]:
    """Providers shown on the leaderboard (columns + counted in totals)."""
    return [p for p in PROVIDERS.values() if p.listed]


def get_provider(slug: str) -> CaptchaProvider:
    """Look up a provider for solving; 404 unknown or no-longer-accepting slugs."""
    from fastapi import HTTPException

    provider = PROVIDERS.get(slug)
    if provider is None or not provider.accepting:
        raise HTTPException(404, f"unknown captcha provider: {slug!r}")
    return provider
