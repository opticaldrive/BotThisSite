# Time-series cache for the graphs page. Reads the SolveEvent history (the
# append-only log), so it's cached with a short TTL like leaderboard_cache.py
# rather than re-scanning on every request.
from datetime import datetime, timedelta

from sqlmodel import select, func
from models import SolveEvent, User
from database import SessionDep
from providers import listed_providers

import time
import threading

# bucket name -> (SQLite strftime format, step between buckets)
BUCKETS: dict[str, tuple[str, timedelta]] = {
    "5min": ("%Y-%m-%d %H:%M", timedelta(minutes=5)),
    "hour": ("%Y-%m-%d %H:00", timedelta(hours=1)),
    "day": ("%Y-%m-%d", timedelta(days=1))
}

_caches: dict[str, dict] = {}  # bucket -> {"ts": ..., "data": ...}
_ttl = 30
_lock = threading.Lock()  # single-flight: only one rebuild at a time # gulp idk waht this is


def _expired(bucket: str, now: float) -> bool:
    entry = _caches.get(bucket)
    return entry is None or now - entry["ts"] > _ttl


def get_solves_series(session: SessionDep, bucket: str = "day"):
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
    if bucket not in BUCKETS:
        bucket = "day"

    now = time.time()
    if _expired(bucket, now):
        # double-checked locking so a herd of requests doesn't all rebuild
        with _lock:
            if _expired(bucket, time.time()):
                _caches[bucket] = {
                    "ts": time.time(),
                    "data": _build_series(session, bucket),
                }
    return _caches[bucket]["data"]


def get_user_solves_series(session: SessionDep, bucket: str = "day"):
    """Total solves per user over time, shaped for Chart.js."""
    if bucket not in BUCKETS:
        bucket = "day"

    fmt, _ = BUCKETS[bucket]
    label = func.strftime(fmt, SolveEvent.solved_at, "unixepoch")
    rows = session.exec(
        select(
            label.label("bucket"),
            User.id,
            User.username,
            func.count().label("count"),
        )
        .join(User, SolveEvent.user_id == User.id)
        .group_by(label, User.id, User.username)
    ).all()

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
            "slug": f"user-{user_id}",
            "name": user_names[user_id],
            "counts": [counts.get(label, {}).get(user_id, 0) for label in labels],
        }
        for user_id in users
    ]
    return {"bucket": bucket, "labels": labels, "series": series}


def _build_series(session: SessionDep, bucket: str):
    fmt, _ = BUCKETS[bucket]
    label = func.strftime(fmt, SolveEvent.solved_at, "unixepoch")
    rows = session.exec(
        select(
            label.label("bucket"),
            SolveEvent.captcha_type,
            func.count().label("count"),
        ).group_by(label, SolveEvent.captcha_type)
    ).all()

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

