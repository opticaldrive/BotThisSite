from sqlmodel import select, func
from sqlalchemy import case
from models import SolveEvent

WINDOWS = {"5min": 300, "1h": 3600, "1day": 86400}


def _window_col(cutoff: int):
    # counts a row only if it's newer than cutoff (bye old rows)
    return func.sum(case((SolveEvent.solved_at >= cutoff, 1), else_=0))


def _query_user_rates(session, user_id: int, now: int):
    cuts = {name: now - secs for name, secs in WINDOWS.items()}
    widest = min(cuts.values())  # the 1day cutoff prunes everything else

    rows = session.exec(
        select(
            SolveEvent.captcha_type,
            _window_col(cuts["5min"]).label("w5min"),
            _window_col(cuts["1h"]).label("w1h"),
            _window_col(cuts["1day"]).label("w1day"),
        )
        .where(SolveEvent.user_id == user_id)
        .where(SolveEvent.solved_at >= widest)  # uses index to prune
        .group_by(SolveEvent.captcha_type)
    ).all()
    return rows


def _shape(rows):
    by_type = {}
    total = {"5min": 0, "1h": 0, "1day": 0}
    for captcha_type, w5, w1h, w1d in rows:
        by_type[captcha_type] = {"5min": w5, "1h": w1h, "1day": w1d}
        total["5min"] += w5
        total["1h"] += w1h
        total["1day"] += w1d
    return {"total": total, "by_type": by_type}
