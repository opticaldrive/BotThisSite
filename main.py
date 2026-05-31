# everything-in-one-file until i fix this mess
from fastapi import FastAPI, Query, Body, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select, desc, func

# validation via http request -> external
import asyncio
import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl
from models import User
from database import SessionDep, create_db_and_tables
from config import CF_SECRET_KEY

ssl_ctx = ssl.create_default_context(
    cafile=certifi.where()
)  # apparently removing this still breaks things uh
app = FastAPI()
# code based on example from fastapi wesbsite


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# app content


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/api/leaderboard")
async def get_leaderboard(session: SessionDep):
    statement = select(User).order_by(desc(User.cloudflare_turnstiles_solved))
    users = session.exec(statement).all()
    print(users)
    return users


@app.get("/api/total_captchas")
async def get_leaderboard(session: SessionDep):
    total_statement = select(func.sum(User.cloudflare_turnstiles_solved))
    total_solved = session.exec(total_statement).one()
    return total_solved


templates = Jinja2Templates(
    directory="templates/"
)  # todo -  move everything to template


# @app.get("/captchas/challenge/cf-turnstile")
@app.get("/leaderboard")
async def serveTurnstile(request: Request, session: SessionDep):
    # a
    # todo: serve htmls
    # return True
    statement = (
        select(User).order_by(desc(User.cloudflare_turnstiles_solved))
        # .limit(100)  # limit 100 t?
    )
    # users = session.exec(statement).all()
    users = session.exec(statement).all()
    total_statement = select(func.sum(User.cloudflare_turnstiles_solved))
    total_solved = session.exec(total_statement).one()
    # print(users)s
    return templates.TemplateResponse(
        request=request,
        name="leaderboard.html",
        context={"users": users, "total_solved": total_solved},
    )


# challenge_pages = Jinja2Templates(directory="src/captchas/challenges")


# @app.get("/captchas/challenge/cf-turnstile")
@app.get("/captchas/cf-turnstile")
async def serveTurnstile(name: str, request: Request):
    # a
    # todo: serve htmls
    # return True
    print(name)
    return templates.TemplateResponse(
        request=request, name="challenges/cf-turnstile.html", context={"name": name}
    )


@app.post("/captchas/verify/cf-turnstile")
async def verifyCFTurnstile(name: str, data: dict, session: SessionDep):  # data: dict):
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
