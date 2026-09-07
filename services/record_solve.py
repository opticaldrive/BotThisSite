import threading
import time

from database import SessionDep
from services.rollup import bump

# This runs once per verify and is the throughput ceiling of the whole service.
# Measured on prattle over a copy of production: sqlite itself does ~12k of
# these a second, the same work through the ORM does ~460. The gap is per-call
# machinery, not the database, so the statements below go to the driver as
# literal SQL. The behaviour is identical to the ORM version that preceded it.
_INSERT_EVENT = "INSERT INTO solveevent (user_id, captcha_type, solved_at) VALUES (?, ?, ?)"

# Atomic "+1" tally: insert the row, or increment it if it already exists. One
# UPSERT so two concurrent solves cannot clobber each other.
_BUMP_COUNT = (
    "INSERT INTO solvecount (user_id, captcha_type, count) VALUES (?, ?, 1) "
    "ON CONFLICT (user_id, captcha_type) DO UPDATE SET count = count + 1"
)

_INSERT_USER = "INSERT OR IGNORE INTO user (username) VALUES (?)"
_SELECT_USER = "SELECT id FROM user WHERE username = ?"

# Usernames map to ids forever, and there are a few hundred of them against
# twenty million solves. Looking one up used to cost two statements on every
# solve, and the first was a write that took sqlite's lock only to do nothing.
_user_ids: dict[str, int] = {}
_user_ids_lock = threading.Lock()


def _user_id(conn, name: str) -> int:
    """Get-or-create, memoised. Only the first solve for a name touches the db."""
    cached = _user_ids.get(name)
    if cached is not None:
        return cached

    # One creator at a time, so a burst of first-solves for a new name does not
    # turn into a burst of identical inserts.
    with _user_ids_lock:
        cached = _user_ids.get(name)
        if cached is not None:
            return cached
        # The insert goes first on purpose: it takes sqlite's write lock before
        # this transaction has read anything, so a process that loses the race
        # is a clean no-op and the select below still sees the winner's row.
        conn.exec_driver_sql(_INSERT_USER, (name,))
        user_id = conn.exec_driver_sql(_SELECT_USER, (name,)).scalar_one()
        _user_ids[name] = user_id
        return user_id


def record_solve(session: SessionDep, name: str, slug: str) -> None:
    """Log the solve: append history (SolveEvent) and bump the tally (SolveCount)."""
    conn = session.connection()
    user_id = _user_id(conn, name)

    # One timestamp for both writes, so the event and its rollup cell can never
    # land in different buckets.
    solved_at = int(time.time())

    conn.exec_driver_sql(_INSERT_EVENT, (user_id, slug, solved_at))  # append-only history
    conn.exec_driver_sql(_BUMP_COUNT, (user_id, slug))

    # the graphs read this, never the raw history
    bump(conn, user_id, slug, solved_at)

    session.commit()
