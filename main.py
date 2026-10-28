from fastapi import FastAPI
import aiohttp

# aiohttp ssl sob macos issues ahhh
import certifi
import ssl

ssl_ctx = ssl.create_default_context(
    cafile=certifi.where()
)  # pls dont remove or my dev env will break


# misc config + core
# from models import User
from database import create_db_and_tables, sqlite_file_name
from services import solve_writer

# routes
from api import leaderboard as api_leaderboard
from api import captchas as api_captchas
from api import graphs as api_graphs
from api import provider_catalog as api_provider_catalog

# pages
from views import homepage as view_homepage
from views import leaderboard as view_leaderboard
from views import challenges as view_challenges
from views import graphs as view_graphs

app = FastAPI()


@app.on_event("startup")
async def on_startup():
    create_db_and_tables()
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
@app.get("/health")
async def health():
    return {"status": "ok"}


# api routers
app.include_router(api_leaderboard.router)
app.include_router(api_captchas.router)  # :3
app.include_router(api_graphs.router)
app.include_router(api_provider_catalog.router)

# page/view roters - these are all ui/html
app.include_router(view_homepage.router)
app.include_router(view_leaderboard.router)
app.include_router(view_challenges.router)
app.include_router(view_graphs.router)
