# everything-in-one-file until i fix this mess
from fastapi import FastAPI, Query, Body, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select

# validation via http request -> external
import asyncio
import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

ssl_ctx = ssl.create_default_context(cafile=certifi.where())

# env vars
import os
from dotenv import load_dotenv

load_dotenv()

CF_SECRET_KEY = os.getenv("CF_SECRET_KEY")

app = FastAPI()
# code based on example from fastapi wesbsite


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    cloudflare_turnstiles_solved: int = Field(default=0)


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# https://ipv4.games/claim?name=whatever
@app.get("/claim")
def claim(name: str, session: SessionDep):
    # if usr hasnt spawned, spawn user
    user = User(username=name)
    statement = select(User).where(User.username == name)  # uh
    user = session.exec(statement).first()

    if not user:  # then user not existy
        user = User(username=name)
        session.add(user)

    user.cloudflare_turnstiles_solved += 1
    print("did it add")
    session.add(user)
    session.commit()
    session.refresh(user)
    # yay we refreshed user
    return user


# app content


@app.get("/")
async def root():
    return {"message": "Hello World"}


challenge_pages = Jinja2Templates(directory="src/captchas/challenges")


# @app.get("/captchas/challenge/cf-turnstile")
@app.get("/captchas/cf-turnstile")
async def serveTurnstile(request: Request):
    # a
    # todo: serve htmls
    # return True
    return challenge_pages.TemplateResponse(request=request, name="cf-turnstile.html")


@app.post("/captchas/verify/cf-turnstile")
async def explodeCFTurnstle(name: str, data: dict, session: SessionDep):  # data: dict):
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
    async with aiohttp.ClientSession() as session:
        async with session.post(url=url, data=data, ssl=ssl_ctx) as response:
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
