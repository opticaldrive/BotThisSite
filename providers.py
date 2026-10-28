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

load_dotenv()

from typing import Literal

SolveMode = Literal["standard", "external", "disabled"]


@dataclass(frozen=True)
class CaptchaProvider:
    slug: str  # url-safe id, e.g. "cf-turnstile". also the SolveCount.captcha_type
    name: str  # human label for the UI, e.g. "Cloudflare Turnstile"
    verify_url: str  # server-side siteverify endpoint
    script_url: str  # <script src> the widget needs
    widget_class: str  # css class the widget script looks for
    site_key_env: str
    secret_key_env: str
    template: str = "challenges/generic.html"  # override for non-standard captchas
    # self-hosted captcha servers (cap) need their base url in the widget too,
    # not just the siteverify call. hosted providers leave this None.
    api_endpoint: str | None = None

    listed: bool = True

    solve_mode: SolveMode = "standard"

    external_challenge_url: str | None = (
        None  # this is a default that stuff like vercel overrides per thingy,  # realisticly idk what would be different from just making this challenge url but whatever
    )

    # we will get it as smt like /captchas/{the slug}?name=demo by default but if url is set, we will redirect solvers to the custom url
    @property
    def challenge_url(self) -> str:
        return self.external_challenge_url or f"/captchas/{self.slug}"

    @property
    def site_key(self) -> str | None:
        return os.getenv(self.site_key_env)

    @property
    def secret_key(self) -> str | None:
        return os.getenv(self.secret_key_env)

    @property
    def solvable(self) -> bool:
        return self.solve_mode != "disabled"


# Where the self-hosted cap server lives. The path segment is the site key cap
# mints, so the whole base has to move together when the server does.
CAP_API_ENDPOINT = (
    os.getenv("CAP_API_ENDPOINT", "https://cap.dunkirk.sh/cbe403f57a").rstrip("/") + "/"
)

# siteverify is server-to-server, so it has no reason to use the public name.
# When cap runs on the same host the public address leaves the interface and
# comes back in through the reverse proxy: cap answers in ~50ms, the proxied
# call takes 1-6s once that proxy is busy, and we make it once per solve.
# Point this at cap's own port and the widget keeps the public URL it needs.
# Defaults to CAP_API_ENDPOINT, so leaving it unset changes nothing.
CAP_VERIFY_ENDPOINT = (
    os.getenv("CAP_VERIFY_ENDPOINT", CAP_API_ENDPOINT).rstrip("/") + "/"
)


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
            solve_mode="standard",
        ),
        CaptchaProvider(
            slug="recaptcha-v2",
            name="reCAPTCHA v2",
            verify_url="https://www.google.com/recaptcha/api/siteverify",
            script_url="https://www.google.com/recaptcha/api.js",
            widget_class="g-recaptcha",
            site_key_env="RECAPTCHA_V2_SITE_KEY",
            secret_key_env="RECAPTCHA_V2_SECRET_KEY",
            # disabled for the sake of my life
            solve_mode="disabled",
        ),
        CaptchaProvider(
            slug="vercel-botid-basic",
            name="Vercel BotID Basic",
            verify_url="",
            script_url="",
            widget_class="",
            site_key_env="",
            secret_key_env="",
            listed=True,
            external_challenge_url="https://botthis.vercel.app/challenge",
            solve_mode="external",
        ),
        CaptchaProvider(
            slug="hcaptcha",
            name="hCaptcha",
            verify_url="https://api.hcaptcha.com/siteverify",
            script_url="https://js.hcaptcha.com/1/api.js",
            widget_class="h-captcha",
            site_key_env="HCAPTCHA_SITE_KEY",
            secret_key_env="HCAPTCHA_SECRET_KEY",
            solve_mode="standard",
        ),
        CaptchaProvider(
            slug="cap-default",
            name="Cap.js Captcha",
            verify_url=f"{CAP_VERIFY_ENDPOINT}siteverify",
            # 0.1.58+ is required to solve hashwx keys (cap 3.1.12+).
            script_url="https://cdn.jsdelivr.net/npm/cap-widget@0.1.58",
            widget_class="",
            site_key_env="CAP_SITE_KEY",
            secret_key_env="CAP_SECRET_KEY",
            template="challenges/cap.html",
            api_endpoint=CAP_API_ENDPOINT,
            solve_mode="standard",
        ),
    ]
}


def solvable_providers() -> list[CaptchaProvider]:
    return [provider for provider in PROVIDERS.values() if provider.solvable]


def listed_providers() -> list[CaptchaProvider]:
    # we can probably get rid of listed anyways its only for a worse case if i mess up
    """Providers shown on the leaderboard (columns + counted in totals)."""
    return [p for p in PROVIDERS.values() if p.listed]


def get_standard_provider(slug: str) -> CaptchaProvider:
    # get a provider for the standard challenge flow
    from fastapi import HTTPException

    provider = PROVIDERS.get(slug)
    if provider is None or provider.solve_mode != "standard":
        raise HTTPException(404, f"unknown captcha provider: {slug!r}")
    return provider
