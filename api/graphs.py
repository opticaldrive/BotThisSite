# Graph data endpoints. These read the SolveEvent history (the append-only log),
# unlike the leaderboard which reads the SolveCount tally.
from datetime import date, timedelta

from fastapi import APIRouter

from sqlmodel import select, func
from models import SolveEvent
from database import SessionDep
from providers import listed_providers

router = APIRouter(prefix="/api/graphs", tags=["stats"])


@router.get("/solves_per_day")
def solves_per_day(session: SessionDep):
    """Total solves bucketed by calendar day (UTC), oldest first.

    solved_at is a Unix timestamp (int), so we let SQLite turn it into a
    YYYY-MM-DD label with strftime(..., 'unixepoch').
    """
    day = func.strftime("%Y-%m-%d", SolveEvent.solved_at, "unixepoch")
    rows = session.exec(
        select(day.label("day"), func.count().label("count"))
        .group_by(day)
        .order_by(day)
    ).all()
    return [{"day": d, "count": c} for d, c in rows]


@router.get("/solves_per_day_by_captcha")
def solves_per_day_by_captcha(session: SessionDep):
    """Daily solves split by captcha type, shaped for a stacked chart.

    Returns a continuous day axis (zero-filled gaps) plus one series per
    *listed* provider, so the frontend can drop it straight into Chart.js:

        {
          "days": ["2026-06-24", "2026-06-25", "2026-06-26"],
          "series": [
            {"slug": "cf-turnstile", "name": "Cloudflare Turnstile",
             "counts": [18, 0, 1]},
            ...
          ]
        }
    """
    day = func.strftime("%Y-%m-%d", SolveEvent.solved_at, "unixepoch")
    rows = session.exec(
        select(
            day.label("day"),
            SolveEvent.captcha_type,
            func.count().label("count"),
        ).group_by(day, SolveEvent.captcha_type)
    ).all()

    # {day: {slug: count}}
    counts: dict[str, dict[str, int]] = {}
    for d, slug, c in rows:
        counts.setdefault(d, {})[slug] = c

    days = _continuous_days(counts.keys())

    # only chart providers we still list on the leaderboard, in registry order
    providers = listed_providers()
    series = [
        {
            "slug": p.slug,
            "name": p.name,
            "counts": [counts.get(d, {}).get(p.slug, 0) for d in days],
        }
        for p in providers
    ]
    return {"days": days, "series": series}


def _continuous_days(day_labels) -> list[str]:
    """Fill in every calendar day between the first and last solve.

    Gives the chart a continuous x-axis instead of skipping days with no
    solves (e.g. 06-24 -> 06-26 keeps the empty 06-25).
    """
    days = sorted(day_labels)
    if not days:
        return []
    start = date.fromisoformat(days[0])
    end = date.fromisoformat(days[-1])
    out: list[str] = []
    cur = start
    while cur <= end:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out
