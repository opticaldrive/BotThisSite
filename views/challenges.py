# leaderboard view? like the html part
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

router = APIRouter(prefix="/captchas", tags=["pages", "challenges"])

templates = Jinja2Templates(
    directory="templates/"
)  # todo -  move everything to template


@router.get("cf-turnstile")
async def serveTurnstile(name: str, request: Request):
    # a
    # todo: serve htmls
    # return True
    print(name)
    return templates.TemplateResponse(
        request=request, name="challenges/cf-turnstile.html", context={"name": name}
    )
