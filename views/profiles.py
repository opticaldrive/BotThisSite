from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates

from sqlmodel import select, desc, func
from models import User
from database import SessionDep
from services.leaderboard_cache import get_stats, captcha_columns

router = APIRouter(prefix="", tags=["pages"])

templates = Jinja2Templates(directory="templates/")


@router.get("/profile")
@router.get("/p")
def get_leaderboard(request: Request, session: SessionDep, name: str):
    # stats = get_stats(session=session)
    # users = stats["data"]
    # if not all:
    #     users = users[:100]

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"name": name},
    )
