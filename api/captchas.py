from fastapi import APIRouter, HTTPException, Request


from sqlmodel import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from models import User, SolveEvent, SolveCount
from database import SessionDep


from services.record_solve import record_solve

from services.utils.cleandata import clean_data
from services.utils.get_ip import get_ip

#
from providers import CaptchaProvider, get_provider

import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

# provider route specific
from api.providers_api import vercel as vercel_api

ssl_ctx = ssl.create_default_context(
    cafile=certifi.where()
)  # apparently removing this still breaks things uh

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/captchas", tags=["challenges"])  # why on earth was it stats

router.include_router(vercel_api.router)


async def siteverify(provider: CaptchaProvider, token: str | None) -> bool:
    """POST {secret, response} to the provider's siteverify endpoint.

    Cloudflare Turnstile, reCAPTCHA and hCaptcha all speak this same protocol
    and return JSON with a boolean "success", so one function covers them all.
    """
    payload = {"secret": provider.secret_key, "response": token}
    async with aiohttp.ClientSession() as aiosession:
        async with aiosession.post(
            url=provider.verify_url, data=payload, ssl=ssl_ctx
        ) as response:
            response.raise_for_status()
            response_json = await response.json()
            print(response_json)
            return response_json.get("success") is True


@router.post("/verify/{slug}")
async def verify_captcha(
    slug: str, name: str, data: dict, session: SessionDep, request: Request
):
    provider = get_provider(slug)
    name = clean_data(name)
    token = data.get("token")
    ip = get_ip(request)
    print(ip)
    print(token)

    # check_failed_verify_allowed(ip)

    if not token or not isinstance(token, str) or not (10 <= len(token) <= 4096):
        # record_failed_verify(ip)
        return {
            "success": False,
            "error-codes": ["invalid-token"],
            "username": name,
        }

    try:
        success = await siteverify(provider, token)
        if success:
            # record_successful_verify(ip)
            record_solve(session, name, slug)
        else:
            # record_failed_verify(ip)
            None
        return {"success": success, "username": name}
    except Exception as e:
        print(f"{provider.name} validation error: {e}")
        return {
            "success": False,
            "error-codes": ["internal-error"],
            "username": name,  # qol
        }
