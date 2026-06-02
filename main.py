# everything-in-one-file until i fix this mess
from fastapi import FastAPI

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

# pages
# homepage:
from views import homepage as view_homepage
from views import leaderboard as view_leaderboard
from views import challenges as view_challenges

# i uh am relying on vscode's "problems" tab without actually verifying so uh gl to me

app = FastAPI()
# code based on example from fastapi wesbsite


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# app content


# @app.get("/")
# async def root():
#     return {"message": "Hello World"}


# api routers
app.include_router(api_leaderboard.router)


app.include_router(api_captchas.router)  # :3

# page/view roters
app.include_router(view_homepage.router)

app.include_router(view_leaderboard.router)

app.include_router(view_challenges.router)
