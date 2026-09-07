# everything-in-one-file until i fix this mess
from fastapi import FastAPI
from sqlmodel import Session
import aiohttp
import logging

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
from database import SessionDep, create_db_and_tables, engine, sqlite_file_name
from services.rollup import backfill
from services import solve_writer

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
    # cheap once caught up, and it repairs the rollup after any downtime.
    with Session(engine) as session:
        written = backfill(session)
    if written:
        logging.getLogger(__name__).info("rollup: wrote %s buckets", written)
    # Every verify makes one of these, so the defaults are the wrong shape:
    # aiohttp would wait five minutes on a slow siteverify while more requests
    # pile in behind the 100-connection cap. A bounded timeout keeps that queue
    # from growing until the process falls over. 30s and not less: cap's own
    # siteverify runs 2.5-8.4s when it is busy, and clients retry on failure,
    # so a tight ceiling turns one slow call into three more requests.
    # The point is to bound the queue, not to police latency.
    app.state.http_session = aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_ctx, limit=256),
        timeout=aiohttp.ClientTimeout(total=30, connect=5),
    )
    # Owns the only connection that writes solves. See services/solve_writer.
    solve_writer.init(sqlite_file_name)


@app.on_event("shutdown")
async def on_shutdown():
    await app.state.http_session.close()
    # Flush the queue before the process goes; anything still in it is lost.
    solve_writer.writer.stop()


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
