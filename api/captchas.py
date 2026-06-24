# One generic verify route for EVERY captcha provider.
# Provider-specific details live in providers.py, not here.
from fastapi import APIRouter

from sqlmodel import select
from models import User, SolveEvent
from database import SessionDep
from services.utils.cleandata import clean_data
from providers import CaptchaProvider, get_provider

import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

ssl_ctx = ssl.create_default_context(
    cafile=certifi.where()
)  # apparently removing this still breaks things uh

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/captchas", tags=["stats"])


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


def record_solve(session: SessionDep, name: str, slug: str) -> None:
    """Make sure the user exists and log one SolveEvent for this captcha."""
    user = session.exec(select(User).where(User.username == name)).first()
    if not user:
        user = User(username=name)
        session.add(user)
        session.flush()  # assigns user.id for new users
    session.add(SolveEvent(user_id=user.id, captcha_type=slug))
    session.commit()


@router.post("/verify/{slug}")
async def verify_captcha(slug: str, name: str, data: dict, session: SessionDep):
    provider = get_provider(slug)
    name = clean_data(name)
    token = data.get("token")
    print(token)

    try:
        success = await siteverify(provider, token)
        if success:
            record_solve(session, name, slug)
        return {"success": success, "username": name}
    except Exception as e:
        print(f"{provider.name} validation error: {e}")
        return {
            "success": False,
            "error-codes": ["internal-error"],
            "username": name,  # qol
        }
