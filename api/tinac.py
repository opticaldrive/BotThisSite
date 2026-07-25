"""Server-side proxy routes for tinac API.

Client-side JS calls /captchas/tinac/challenge and /captchas/tinac/verify
which are proxied to the real tinac backend at https://tanjim.org:525.
This way the tinac API key/URL is never exposed to the browser.
"""

from fastapi import APIRouter, Request
import aiohttp

import certifi
import ssl

from models import User, SolveEvent, SolveCount
from database import SessionDep
from services.utils.cleandata import clean_data
from sqlmodel import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

ssl_ctx = ssl.create_default_context(cafile=certifi.where())

TINAC_API_BASE = "https://tanjim.org:525"

router = APIRouter(prefix="/captchas/tinac", tags=["tinac-proxy"])

TINAC_SLUG = "tinac"


def record_solve(session: SessionDep, name: str) -> None:
    """Log the solve: append history (SolveEvent) and bump the tally (SolveCount)."""
    user = session.exec(select(User).where(User.username == name)).first()
    if not user:
        user = User(username=name)
        session.add(user)
        session.flush()

    session.add(SolveEvent(user_id=user.id, captcha_type=TINAC_SLUG))

    upsert = (
        sqlite_insert(SolveCount)
        .values(user_id=user.id, captcha_type=TINAC_SLUG, count=1)
        .on_conflict_do_update(
            index_elements=["user_id", "captcha_type"],
            set_={"count": SolveCount.count + 1},
        )
    )
    session.execute(upsert)
    session.commit()


@router.get("/challenge")
async def proxy_challenge_img():
    """Proxy GET /challenge_img from the tinac API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{TINAC_API_BASE}/challenge_img", ssl=ssl_ctx
        ) as resp:
            data = await resp.json()
            return data


@router.post("/verify")
async def proxy_verify(
    name: str, data: dict, session: SessionDep, request: Request
):
    """Proxy POST /verify to the tinac API, then record solve if correct.

    Client sends: {id, answer, index}
    tinac returns: {answer: bool, index: bool, token: string}
    """
    name = clean_data(name)

    tinac_id = data.get("id")
    answer = data.get("answer")
    index = data.get("index")

    if not tinac_id or answer is None:
        return {"error": "id and answer parameters required"}

    payload = {"id": tinac_id, "answer": answer}
    if index is not None:
        payload["index"] = index

    try:
        async with aiohttp.ClientSession() as aiosession:
            async with aiosession.post(
                f"{TINAC_API_BASE}/verify", json=payload, ssl=ssl_ctx
            ) as resp:
                tinac_result = await resp.json()

        success = tinac_result.get("answer") is True
        if success:
            record_solve(session, name)

        return {
            "success": success,
            "username": name,
            "answer_correct": tinac_result.get("answer"),
            "index_correct": tinac_result.get("index"),
            "token": tinac_result.get("token"),
        }
    except Exception as e:
        print(f"tinac verification error: {e}")
        return {
            "success": False,
            "error": "internal-error",
            "username": name,
        }
