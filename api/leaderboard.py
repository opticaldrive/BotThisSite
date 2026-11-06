from fastapi import APIRouter
from database import SessionDep

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


@router.get("/totals_by_type_json")
def get_total_captchas_by_type_json(session: SessionDep):
    stats = get_stats(session=session)
    return stats["totals_by_type"]
