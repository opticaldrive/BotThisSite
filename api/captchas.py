# copypasta sob s
# leaderboard + stats wrapped in here
# everything-in-one-file until i fix this mess
from fastapi import APIRouter


from sqlmodel import select, desc, func
from models import User
from database import SessionDep

from config import CF_SECRET_KEY
import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

ssl_ctx = ssl.create_default_context(
    cafile=certifi.where()
)  # apparently removing this still breaks things uh
# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/captchas", tags=["stats"])


@router.post("/verify/cf-turnstile")
async def verify_cf_turnstile(
    name: str, data: dict, session: SessionDep
):  # data: dict):
    # this is NOT the right approach to get query and body lol
    # ig i need types and stuff, tmr
    # rn its just curl -X POST  "localhost:8000/captchas/verify/cf-turnstile?token=mrrp"
    token = data.get("token")
    print(token)

    # fix body logic above

    # cf: POST https://challenges.cloudflare.com/turnstile/v0/siteverify
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = {
        "secret": CF_SECRET_KEY,  # secret, i spent too long doing dotenv
        "response": token,
    }
    async with aiohttp.ClientSession() as aiosession:
        async with aiosession.post(url=url, data=data, ssl=ssl_ctx) as response:
            try:
                response.raise_for_status()
                response_json = await response.json()
                print(response_json)
                if response_json["success"] == True:
                    None
                    # user cf count ++
                    user = User(username=name)
                    statement = select(User).where(User.username == name)  # uh
                    user = session.exec(statement).first()

                    if not user:  # then user not existy
                        user = User(username=name)
                        session.add(user)

                    user.cloudflare_turnstiles_solved += 1
                    print("did it add to ", user)
                    session.add(user)
                    session.commit()
                    session.refresh(user)
                response_json["uesrname"] = name
                return response_json
            except Exception as e:
                print(f"Turnstile validation error: {e}")
                return {
                    "success": False,
                    "error-codes": ["internal-error"],
                    "username": name,
                }
