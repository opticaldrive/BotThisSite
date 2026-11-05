from sqlmodel import select
from models import User, SolveCount
from database import SessionDep
from providers import listed_providers

import time
import threading

_cache = {
    "ts": 0,
    "data": None,
    "total_solved": None,
    "totals_by_type": None,
    "cache_age": None,
}
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
    rows = session.exec(
        select(
            User.id,
            User.username,
            SolveCount.captcha_type,
            SolveCount.count,
        ).join(SolveCount, SolveCount.user_id == User.id)
    ).all()

    providers = listed_providers()
    totals_by_type = {p.slug: 0 for p in providers}
    shown = set(p.slug for p in providers)

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
        totals_by_type[
            captcha_type
        ] += count  # maybe we can do this on orm/db side, not on cache builds.

    users = sorted(users_by_id.values(), key=lambda u: u["total"], reverse=True)

    _cache["data"] = users
    _cache["ts"] = time.time()
    _cache["total_solved"] = sum(u["total"] for u in users)
    _cache["totals_by_type"] = totals_by_type
