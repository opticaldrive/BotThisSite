from fastapi import APIRouter, HTTPException, Request


from sqlmodel import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from models import User, SolveEvent, SolveCount
from database import SessionDep


from services import solve_writer

from services.utils.cleandata import clean_data
from services.utils.get_ip import get_ip

#
from providers import CaptchaProvider, get_provider

import asyncio
import aiohttp
import logging

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

# provider route specific
from api.providers_api import vercel as vercel_api

ssl_ctx = ssl.create_default_context(
    cafile=certifi.where()
)  # apparently removing this still breaks things uh

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

log = logging.getLogger(__name__)

router = APIRouter(prefix="/captchas", tags=["challenges"])  # why on earth was it stats

router.include_router(vercel_api.router)


async def siteverify(
    provider: CaptchaProvider, token: str | None, aiosession: aiohttp.ClientSession
) -> bool:
    """POST {secret, response} to the provider's siteverify endpoint.

    Cloudflare Turnstile, reCAPTCHA and hCaptcha all speak this same protocol
    and return JSON with a boolean "success", so one function covers them all.
    """
    payload = {"secret": provider.secret_key, "response": token}
    async with aiosession.post(
        url=provider.verify_url, data=payload, ssl=ssl_ctx
    ) as response:
        response.raise_for_status()
        response_json = await response.json()
        log.debug("%s siteverify: %s", provider.name, response_json)
        return response_json.get("success") is True


@router.post("/verify/{slug}")
async def verify_captcha(
    slug: str, name: str, data: dict, session: SessionDep, request: Request
):
    provider = get_provider(slug)
    name = clean_data(name)
    token = data.get("token")
    ip = get_ip(request)
    # the token is a credential, so it stays out of the log. debug, not info:
    # this is the hot path, and at solver load an info line here is hundreds of
    # journald writes a second. Caddy's access log already has the IPs.
    log.debug("verify %s for %r from %s", slug, name, ip)

    # check_failed_verify_allowed(ip)

    if not token or not isinstance(token, str) or not (10 <= len(token) <= 4096):
        # record_failed_verify(ip)
        return {
            "success": False,
            "error-codes": ["invalid-token"],
            "username": name,
        }

    try:
        success = await siteverify(provider, token, request.app.state.http_session)
        if success:
            # record_successful_verify(ip)
            # Hands the solve to the single writer thread and returns. It used
            # to run the transaction here on a threadpool thread, which meant
            # every in-flight verify was another thread competing for sqlite's
            # write lock, and the queueing for that lock was most of the
            # endpoint's latency. The solve is durable a batch later, not now.
            solve_writer.record(name, slug)
        else:
            # record_failed_verify(ip)
            None
        return {"success": success, "username": name}
    except (asyncio.TimeoutError, aiohttp.ClientError) as e:
        # The provider being slow or unreachable is an operating condition, not
        # a surprise. log.exception here writes a ~15 line traceback per failed
        # verify, so a provider having a bad minute buries the journal in the
        # one thing it already knows. One line, and keep the traceback for
        # errors that are actually unexpected.
        # status + message only. repr() of a ClientResponseError carries every
        # request and response header, which is a 900 character "one line".
        detail = (
            f"HTTP {e.status} {e.message}"
            if isinstance(e, aiohttp.ClientResponseError)
            else type(e).__name__
        )
        log.warning("%s siteverify unavailable: %s", provider.name, detail)
        return {
            "success": False,
            "error-codes": ["internal-error"],
            "username": name,
        }
    except Exception as e:
        log.exception("%s validation error: %s", provider.name, e)
        return {
            "success": False,
            "error-codes": ["internal-error"],
            "username": name,  # qol
        }
