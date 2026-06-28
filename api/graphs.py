# Graph data endpoints. These read the SolveEvent history (the append-only log),
# unlike the leaderboard which reads the SolveCount tally. Aggregation + caching
# live in services/graph_cache.py.
from fastapi import APIRouter

from database import SessionDep
from services.graph_cache import get_solves_series

router = APIRouter(prefix="/api/graphs", tags=["stats"])


@router.get("/solves")
def solves(session: SessionDep, bucket: str = "day"):
    """Solves per time bucket, split by captcha type. bucket = hour | day."""
    return get_solves_series(session, bucket)
