from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool


from sqlmodel import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from models import User, SolveEvent, SolveCount
from database import SessionDep


from services.record_solve import record_solve

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
            # record_solve is synchronous sqlite: a SELECT, two writes and a
            # commit. Called directly it would run on the event loop and stall
            # every other in-flight request for the length of the transaction,
            # which under WAL contention is up to busy_timeout (5s).
            await run_in_threadpool(record_solve, session, name, slug)
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
        log.warning("%s siteverify unavailable: %r", provider.name, e)
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
