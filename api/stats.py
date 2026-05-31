# refactor complete, minor route changes tbd + per user profiles
# leaderboard + stats wrapped in here
# everything-in-one-file until i fix this mess
from fastapi import FastAPI, Query, Body, Request, APIRouter
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import select, desc, func
from models import User
from database import SessionDep

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/api/", tags=["stats"])


@router.get("/leaderboard")
async def get_leaderboard(session: SessionDep):
    statement = select(User).order_by(desc(User.cloudflare_turnstiles_solved))
    users = session.exec(statement).all()
    print(users)
    return users


@router.get("/total_captchas")
async def get_total_captchas(session: SessionDep):
    total_statement = select(func.sum(User.cloudflare_turnstiles_solved))
    total_solved = session.exec(total_statement).one()
    return total_solved
