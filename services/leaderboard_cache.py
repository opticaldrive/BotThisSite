from sqlmodel import select, desc, func
from models import User
from database import SessionDep

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
    if (
        _cache["data"] is None or now - _cache["ts"] > _ttl
    ):  # nonexistant cache!/updateudpate
        statement = (
            select(User).order_by(desc(User.cloudflare_turnstiles_solved))
            # .limit(100)  # limit 100 t?
        )
        # users = session.exec(statement).all()
        users = session.exec(statement).all()

        total_statement = select(func.sum(User.cloudflare_turnstiles_solved))
        total_solved = session.exec(total_statement).one()
        _cache["data"] = users
        _cache["ts"] = now
        _cache["total_solved"] = total_solved
