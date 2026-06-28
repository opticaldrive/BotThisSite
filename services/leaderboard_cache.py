from sqlmodel import select
from models import User, SolveCount
from database import SessionDep
from providers import listed_providers

import time
import threading

_cache = {"ts": 0, "data": None, "total_solved": None, "cache_age": None}
_ttl = 30
_lock = threading.Lock()  # single-flight: only one rebuild at a time


def _expired(now: float) -> bool:
    return _cache["data"] is None or now - _cache["ts"] > _ttl


def get_stats(session: SessionDep):
    # literally th only thing i need to access thumbsup
    now = time.time()
    if _expired(now):
        # double-checked locking so a herd of requests doesn't all rebuild
        with _lock:
            if _expired(time.time()):
                update_stat_cache(session=session)
    _cache["cache_age"] = max(int(now - _cache["ts"]), 0)
    return _cache


def update_stat_cache(session: SessionDep):
    # Reads the SolveCount tally (~ #users * #captcha types rows), NOT the full
    # SolveEvent history, so this stays fast no matter how many solves exist.
    rows = session.exec(
        select(
            User.id,
            User.username,
            SolveCount.captcha_type,
            SolveCount.count,
        ).join(SolveCount, SolveCount.user_id == User.id)
    ).all()

    # only count captcha types we still show on the leaderboard, so the grand
    # total and each user's total always equal the sum of the visible columns.
    # (unlisted providers' rows stay in the DB, just excluded from the view.)
    shown = {p.slug for p in listed_providers()}

    # build {user_id: {"username":..., "total":..., "by_type": {...}}}
    users_by_id: dict[int, dict] = {}
    for user_id, username, captcha_type, count in rows:
        if captcha_type not in shown:
            continue
        entry = users_by_id.setdefault(
            user_id,
            {"username": username, "total": 0, "by_type": {}},
        )
        entry["by_type"][captcha_type] = count
        entry["total"] += count

    users = sorted(users_by_id.values(), key=lambda u: u["total"], reverse=True)

    _cache["data"] = users
    _cache["ts"] = time.time()
    _cache["total_solved"] = sum(u["total"] for u in users)


# the captcha types to show as columns on the leaderboard, in registry order.
# unlisted providers are hidden here but their counts remain in the DB.
def captcha_columns():
    return listed_providers()
