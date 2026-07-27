from fastapi import APIRouter, HTTPException, Request, Header


from sqlmodel import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from models import User, SolveEvent, SolveCount
from database import SessionDep

from services.utils.cleandata import clean_data
from services.utils.get_ip import get_ip

from services.record_solve import record_solve
import os
import hmac

#
from providers import CaptchaProvider, get_provider

import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

ssl_ctx = ssl.create_default_context(cafile=certifi.where())
router = APIRouter(prefix="/record/vercel", tags=["misc"])  # why on earth was it stats


@router.post("/botid-basic")
async def record_botid_basic(
    name: str,
    session: SessionDep,
    request: Request,
    x_botid_secret: str | None = Header(
        default=None,
        alias="X-BotID-Secret",
    ),
):
    # provider = get_provider("vercel-botid-basic")

    stored_secret = os.getenv("BOTID_SHARED_SECRET")

    if not stored_secret:
        raise HTTPException(
            status_code=503,
            detail="ya we might have forgotten to configure vercel botid somewhere here",
        )

    if x_botid_secret is None or not hmac.compare_digest(x_botid_secret, stored_secret):
        raise HTTPException(
            status_code=403,
            detail="forbidden go away smh",
        )

    name = clean_data(name)
    ip = get_ip(request)
    print(ip)
    record_solve(session, name, "vercel-botid-basic")

    return {"success": True, "username": name}
