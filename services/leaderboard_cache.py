from sqlmodel import select, func
from models import User, SolveEvent
from database import SessionDep
from providers import PROVIDERS

import time

_cache = {"ts": 0, "data": None, "total_solved": None, "cache_age": None}
_ttl = 30


def get_stats(session: SessionDep):
    # literally th only thing i need to access thumbsup
    now = time.time()
    if _cache["data"] is None or now - _cache["ts"] > _ttl:
        update_stat_cache(session=session)
    _cache["cache_age"] = max(int(now - _cache["ts"]), 0)

    return _cache


def update_stat_cache(session: SessionDep):
    now = time.time()
    if _cache["data"] is None or now - _cache["ts"] > _ttl:
        # Counts are derived from SolveEvent, so any captcha registered in
        # providers.py shows up automatically with no schema change.
        rows = session.exec(
            select(
                User.id,
                User.username,
                SolveEvent.captcha_type,
                func.count(SolveEvent.id),
            )
            .join(SolveEvent, SolveEvent.user_id == User.id)
            .group_by(User.id, SolveEvent.captcha_type)
        ).all()

        # build {user_id: {"username":..., "total":..., "by_type": {...}}}
        users_by_id: dict[int, dict] = {}
        for user_id, username, captcha_type, count in rows:
            entry = users_by_id.setdefault(
                user_id,
                {"username": username, "total": 0, "by_type": {}},
            )
            entry["by_type"][captcha_type] = count
            entry["total"] += count

        users = sorted(
            users_by_id.values(), key=lambda u: u["total"], reverse=True
        )

        _cache["data"] = users
        _cache["ts"] = now
        _cache["total_solved"] = sum(u["total"] for u in users)


# the captcha types to show as columns on the leaderboard, in registry order
def captcha_columns():
    return list(PROVIDERS.values())
