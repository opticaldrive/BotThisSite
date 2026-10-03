from fastapi import APIRouter, HTTPException, Request, Header


from services.utils.cleandata import clean_data
from services.utils.get_ip import get_ip

from services import solve_writer
import os
import hmac
import logging

#
from providers import CaptchaProvider, get_provider

import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

ssl_ctx = ssl.create_default_context(cafile=certifi.where())
log = logging.getLogger(__name__)

router = APIRouter(prefix="/record/vercel", tags=["misc"])  # why on earth was it stats


@router.post("/botid-basic")
@router.get("/botid-basic")
async def record_botid_basic(
    name: str,
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
    log.info("botid solve for %r from %s", name, ip)
    # Same queue as the cap path: one writer for the database, or the two of
    # them go back to competing for sqlite's write lock.
    solve_writer.record(name, "vercel-botid-basic")

    return {"success": True, "username": name}
