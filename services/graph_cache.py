# Time-series cache for the graphs page. Reads SolveBucket, the 5-minute
# rollup (see services/rollup.py), so a rebuild groups a few thousand rows
# instead of the millions of per-solve rows this used to cost. Still cached
# with a short TTL like leaderboard_cache.py.
from datetime import datetime, timedelta

from sqlmodel import select, func
from models import SolveBucket, User, SolveCount
from database import SessionDep
from providers import listed_providers
from fastapi import HTTPException
import time
import threading

# bucket name -> (SQLite strftime format, step between buckets)
BUCKETS: dict[str, tuple[str, timedelta]] = {
    "5min": ("%Y-%m-%d %H:%M", timedelta(minutes=5)),
    "hour": ("%Y-%m-%d %H:00", timedelta(hours=1)),
    "day": ("%Y-%m-%d", timedelta(days=1)),
}

RANGES = {
    # if i keep adding more the cache is just gonna keep getting bigger lol
    # maybe just have everything in segments idkk i'll figure it out when i run out of RAM
    "hour": 3600,
    "day": 86400,
    "3day": 3 * 86400,
    "7day": 7 * 86400,
    "30day": 30 * 86400,
    "all": None,
}

# restrict the dangerous 5min x all query that never seems to finish
ALLOWED_RANGES = {
    # left - buckets, right, ranges
    "5min": {
        "hour",
        "day",
        "3day",
    },
    "hour": {"day", "3day", "7day"},
    "day": {"3day", "7day", "30day", "all"},
}


def validate_range_combo(bucket: str, range: str):
    if bucket not in ALLOWED_RANGES:
        raise HTTPException(
            status_code=422, detail=f"can't have this bucket, sorry: {bucket}"
        )
    if range not in ALLOWED_RANGES[bucket]:
        allowed = sorted(ALLOWED_RANGES[bucket])
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"can't have this range, sorry: {range}",
                "allowed_ranges": allowed,
            },
        )


def _bucket_label(bucket: str):
    """SQL expression: floor solved_at to the bucket boundary, then format it.

    strftime alone can't express "every 5 minutes" (its finest field is a whole
    minute), so we floor the unix timestamp to a multiple of the step size
    *before* formatting. This makes the SQL grouping land on the same boundaries
    that _continuous_labels walks, so no solves get dropped.
    """
    fmt, step = BUCKETS[bucket]
    step_seconds = int(step.total_seconds())
    floored = SolveBucket.bucket_start - (SolveBucket.bucket_start % step_seconds)
    return func.strftime(fmt, floored, "unixepoch")


def _range_filter(query, range: str):
    """Restrict a rollup query to the last N seconds ("all" -> no filter).

    The cutoff is computed here at build time, so the window advances in _ttl-
    second jumps as the cache rebuilds (which is why range is part of the key).
    """
    seconds = RANGES.get(range)
    if seconds is not None:
        cutoff = int(time.time()) - seconds
        # bucket_start leads the primary key, so this prunes on the index
        query = query.where(SolveBucket.bucket_start >= cutoff)
    return query


_caches: dict[str, dict] = {}  # bucket -> {"ts": ..., "data": ...}
_ttl = 60
_lock = (
    threading.Lock()
)  # single-flight: only one rebuild at a time # gulp idk waht this is


def _expired(key: str, now: float) -> bool:
    entry = _caches.get(key)
    return entry is None or now - entry["ts"] > _ttl


def _cache_key(kind: str, bucket: str, range: str) -> str:
    # warning - 9 x captchas can scale up later, might want to investigate.
    # this variable cahce thing is so dubm lollll
    return f"{kind}:{bucket}:{range}"


def _cached(kind: str, bucket: str, range: str, builder, session: SessionDep):
    """Shared TTL cache + single-flight rebuild used by both graph endpoints.

    `builder(session, bucket, range)` does the actual DB work; we just memoize
    its result per (kind, bucket, range) for _ttl seconds.
    """
    validate_range_combo(bucket, range)

    key = _cache_key(kind, bucket, range)
    if _expired(key, time.time()):
        # double-checked locking so a herd of requests doesn't all rebuild
        with _lock:
            if _expired(key, time.time()):
                _caches[key] = {
                    "ts": time.time(),
                    "data": builder(session, bucket, range),
                }
    return _caches[key]["data"]


def get_solves_series(session: SessionDep, bucket: str = "day", range: str = "all"):
    """Solves per time bucket, split by captcha type, shaped for Chart.js.

    {
      "bucket": "day",
      "labels": ["2026-06-24", "2026-06-25", ...],
      "series": [
        {"slug": "cf-turnstile", "name": "Cloudflare Turnstile",
         "counts": [17, 0, ...]},
        ...
      ]
    }
    """
    return _cached("solves", bucket, range, _build_series, session)


def get_user_solves_series(
    session: SessionDep, bucket: str = "day", range: str = "all"
):
    """Total solves per user over time, shaped for Chart.js."""
    return _cached("user", bucket, range, _build_user_series, session)


def get_user_scores_series(
    session: SessionDep, bucket: str = "day", range: str = "all"
):
    """"""
    return _cached("user-scores", bucket, range, _build_user_score_series, session)


def _build_user_series(session: SessionDep, bucket: str, range: str):
    label = _bucket_label(bucket)
    q = select(
        label.label("bucket"),
        User.id,
        User.username,
        func.sum(SolveBucket.count).label("count"),
    ).join(User, SolveBucket.user_id == User.id)
    q = _range_filter(q, range).group_by(label, User.id, User.username)
    rows = session.exec(q).all()

    counts: dict[str, dict[int, int]] = {}
    user_names: dict[int, str] = {}
    totals: dict[int, int] = {}
    for bucket_label, user_id, username, count in rows:
        counts.setdefault(bucket_label, {})[user_id] = count
        user_names[user_id] = username
        totals[user_id] = totals.get(user_id, 0) + count

    labels = _continuous_labels(counts.keys(), bucket)

    # show the users with the highest total solves first
    users = sorted(totals.keys(), key=lambda uid: totals[uid], reverse=True)

    series = [
        {
            "user_id": user_id,
            "name": user_names[user_id],
            "counts": [counts.get(label, {}).get(user_id, 0) for label in labels],
        }
        for user_id in users
    ]
    return {"bucket": bucket, "labels": labels, "series": series}


def _build_user_score_series(session: SessionDep, bucket: str, range: str):
    based = _build_user_series(session, bucket, range)

    tally = dict(
        session.exec(
            select(SolveCount.user_id, func.sum(SolveCount.count)).group_by(
                SolveCount.user_id
            )
        ).all()
    )

    series = []
    for s in based["series"]:
        window_total = sum(s["counts"])
        # anchor so the last point == the user's true all-time total (SolveCount,
        # which includes the ~200k pre-history solves). the missing history
        # becomes the flat starting plateau instead of being approximated.
        running = tally.get(s["user_id"], 0) - window_total
        cumulative = []
        for c in s["counts"]:
            running += c
            cumulative.append(running)
        series.append({**s, "counts": cumulative})
    return {"bucket": based["bucket"], "labels": based["labels"], "series": series}


def _build_series(session: SessionDep, bucket: str, range: str):
    label = _bucket_label(bucket)
    q = select(
        label.label("bucket"),
        SolveBucket.captcha_type,
        func.sum(SolveBucket.count).label("count"),
    )
    q = _range_filter(q, range).group_by(label, SolveBucket.captcha_type)
    rows = session.exec(q).all()

    # {label: {slug: count}}
    counts: dict[str, dict[str, int]] = {}
    for b, slug, c in rows:
        counts.setdefault(b, {})[slug] = c

    labels = _continuous_labels(counts.keys(), bucket)

    # only chart providers we still list on the leaderboard, in registry order
    series = [
        {
            "slug": p.slug,
            "name": p.name,
            "counts": [counts.get(b, {}).get(p.slug, 0) for b in labels],
        }
        for p in listed_providers()
    ]
    return {"bucket": bucket, "labels": labels, "series": series}


def _continuous_labels(raw_labels, bucket: str) -> list[str]:
    """Fill in every bucket between the first and last solve.
    # idk if i want this - review - slop
    Keeps a continuous x-axis instead of skipping empty buckets (e.g. a day or
    hour with no solves still shows as a zero).
    """
    labels = sorted(raw_labels)
    if not labels:
        return []
    fmt, step = BUCKETS[bucket]
    cur = datetime.strptime(labels[0], fmt)
    end = datetime.strptime(labels[-1], fmt)
    out: list[str] = []
    while cur <= end:
        out.append(cur.strftime(fmt))
        cur += step
    return out
