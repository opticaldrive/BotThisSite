# Graph data endpoints. These read SolveBucket, the 5-minute rollup, much as the
# leaderboard reads the SolveCount tally: neither one touches the SolveEvent
# history. Aggregation + caching live in services/graph_cache.py.
from fastapi import APIRouter

from database import SessionDep
from services.graph_cache import (
    get_solves_series,
    get_user_solves_series,
    get_user_scores_series,
)

router = APIRouter(prefix="/api/graphs", tags=["stats"])


@router.get("/solves")
def solves(session: SessionDep, bucket: str = "day", range: str = "all"):
    """Solves per time bucket, split by captcha type. bucket = hour | day."""
    return get_solves_series(session, bucket, range)


@router.get("/user-solves")
def user_solves(session: SessionDep, bucket: str = "day", range: str = "all"):
    """Total solves per user over time. bucket = hour | day."""
    return get_user_solves_series(session, bucket, range)


@router.get("/user-scores")
def user_scores(session: SessionDep, bucket: str = "day", range: str = "all"):
    """Cumulative solves (score) per user over time. bucket = hour | day."""
    return get_user_scores_series(session, bucket, range)
