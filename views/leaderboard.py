from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates

from sqlmodel import select, desc, func
from models import User
from database import SessionDep
from services.leaderboard_cache import get_stats

router = APIRouter(prefix="/leaderboard", tags=["pages"])

templates = Jinja2Templates(directory="templates/")


@router.get("")
def get_leaderboard(request: Request, session: SessionDep, all: bool | None = False):
    stats = get_stats(session=session)
    users = stats["data"]
    if not all:
        users = users[:10]

    return templates.TemplateResponse(
        request=request,
        name="leaderboard.html",
        context={
            "users": users,
            "total_solved": stats["total_solved"],
            "cache_age": stats["cache_age"],
        },
    )
