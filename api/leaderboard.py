# refactor complete, minor route changes tbd + per user profiles
# leaderboard + stats wrapped in here
# everything-in-one-file until i fix this mess
from fastapi import APIRouter

from sqlmodel import select, desc, func
from models import User
from database import SessionDep

# https://fastapi.tiangolo.com/tutorial/bigger-applications/#import-apirouter

router = APIRouter(prefix="/api", tags=["stats"])

from services.leaderboard_cache import get_stats


@router.get("/leaderboard")
def get_leaderboard(session: SessionDep):
    return get_stats(session=session)


@router.get("/total_captchas")
def get_total_captchas(session: SessionDep):
    stats = get_stats(session=session)
    return stats["total_solved"]


@router.get("/total_captchas_json")  # jank but im lazy
def get_total_captchas_json(session: SessionDep):
    stats = get_stats(session=session)
    # return stats["total_solved"]
    return {"total_solved": stats["total_solved"]}
