# everything-in-one-file until i fix this mess
from fastapi import FastAPI
import aiohttp

# validation via http request -> external

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

ssl_ctx = ssl.create_default_context(
    cafile=certifi.where()
)  # apparently removing this still breaks things uh

# custom omdules for now

# misc config + core
# from models import User
from database import SessionDep, create_db_and_tables

# from config import CF_SECRET_KEY


# routes
from api import leaderboard as api_leaderboard
from api import captchas as api_captchas
from api import graphs as api_graphs

# pages
# homepage:
from views import homepage as view_homepage
from views import leaderboard as view_leaderboard
from views import challenges as view_challenges
from views import graphs as view_graphs

app = FastAPI()

# code based on example from fastapi wesbsite


@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
    app.state.http_session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_ctx)
    )


@app.on_event("shutdown")
async def on_shutdown():
    await app.state.http_session.close()


# app content


# @app.get("/")
# async def root():
#     return {"message": "Hello World"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# api routers
app.include_router(api_leaderboard.router)


app.include_router(api_captchas.router)  # :3

app.include_router(api_graphs.router)

# page/view roters - these are all ui/html
app.include_router(view_homepage.router)

app.include_router(view_leaderboard.router)

app.include_router(view_challenges.router)

app.include_router(view_graphs.router)
