from sqlmodel import select, desc, func
from models import User
from database import SessionDep

import time

cache = {"ts": 0, "data": None, "total_solved": None}
ttl = 30


def update_stat_cache(session: SessionDep):
    current_time = time.time()
    if (
        cache["data"] is None or current_time - cache["ts"] > ttl
    ):  # nonexistant cache!/updateudpate
        statement = (
            select(User).order_by(desc(User.cloudflare_turnstiles_solved))
            # .limit(100)  # limit 100 t?
        )
        # users = session.exec(statement).all()
        users = session.exec(statement).all()

        total_statement = select(func.sum(User.cloudflare_turnstiles_solved))
        total_solved = session.exec(total_statement).one()
        cache["data"] = users
        cache["ts"] = current_time
        cache["total_solved"] = total_solved
