# copypasta sob s
# leaderboard + stats wrapped in here
# everything-in-one-file until i fix this mess
from fastapi import APIRouter, HTTPException


from sqlmodel import select, desc, func
from models import User
from database import SessionDep

from config import CF_SECRET_KEY, RECAPTCHA_V2_SECRET_KEY
import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

import unicodedata


def clean_data(raw: str):
    stringy = unicodedata.normalize("NFKC", (raw or "")).strip()
    if not (1 <= len(stringy) <= 64):
        print("out of lengthy")
        raise HTTPException(
            400,
            "the name you have given me is simply too long, or simply too short. or nonexistant",
        )
    if any(unicodedata.category(c).startswith("C") for c in stringy):
        print("controlly chars ew")
        raise HTTPException(400, "name has control characters smh")
    return stringy


ssl_ctx = ssl.create_default_context(
    cafile=certifi.where()
)  # apparently removing this still breaks things uh
# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/captchas", tags=["stats"])


@router.post("/verify/cf-turnstile")
async def verify_cf_turnstile(name: str, data: dict, session: SessionDep):
    name = clean_data(name)

    token = data.get("token")
    print(token)

    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = {
        "secret": CF_SECRET_KEY,  # secret, i spent too long doing dotenv
        "response": token,
    }

    try:
        async with aiohttp.ClientSession() as aiosession:
            async with aiosession.post(url=url, data=data, ssl=ssl_ctx) as response:
                response.raise_for_status()
                response_json = await response.json()
                print(response_json)
                if response_json["success"] == True:
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
                response_json["username"] = name
                return response_json
    except Exception as e:
        print(f"Turnstile validation error: {e}")
        return {
            "success": False,
            "error-codes": ["internal-error"],
            "username": name,
        }


# on hold until database is ready

# @router.post("/verify/recaptcha-v2")
# async def verify_recaptcha_v2(name: str, data: dict, session: SessionDep):
#     name = clean_data(name)
#     token = data.get("token")
#     print(token)

#     url = "https://www.google.com/recaptcha/api/siteverify"
#     data = {
#         "secret": RECAPTCHA_V2_SECRET_KEY,  # secret, i spent too long doing dotenv
#         "response": token,
#     }

#     try:
#         async with aiohttp.ClientSession() as aiosession:
#             async with aiosession.post(url=url, data=data, ssl=ssl_ctx) as response:
#                 response.raise_for_status()
#                 response_json = await response.json()
#                 print(response_json)
#                 # on hold until database is ready
#                 # if response_json["success"] == True:
#                 #     user = User(username=name)
#                 #     statement = select(User).where(User.username == name)  # uh
#                 #     user = session.exec(statement).first()

#                 #     if not user:  # then user not existy
#                 #         user = User(username=name)
#                 #         session.add(user)

#                 #     user.cloudflare_turnstiles_solved += 1
#                 #     print("did it add to ", user)
#                 #     session.add(user)
#                 #     session.commit()
#                 #     session.refresh(user)
#                 response_json["username"] = name
#                 return response_json
#     except Exception as e:
#         print(f"Recaptcha validation error: {e}")
#         return {
#             "success": False,
#             "error-codes": ["internal-error"],
#             "username": name,
#         }
