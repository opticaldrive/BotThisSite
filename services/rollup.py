# The graphs used to group 5M+ SolveEvent rows by a computed strftime
# expression on every cache rebuild, which no index can help with. They read
# SolveBucket instead: the same history pre-aggregated into 5-minute cells,
# roughly three orders of magnitude fewer rows.
#
# Two ways in, and they must agree: record_solve() bumps a cell as each solve
# lands, and backfill() recomputes cells from SolveEvent. Since the rollup is
# only ever a function of the history, backfill can always repair it.
from sqlalchemy import text

GRAIN = 300  # seconds; the finest bucket the graphs offer ("5min")


def bucket_of(ts: int) -> int:
    """Floor a unix timestamp to the start of its rollup cell."""
    return ts - (ts % GRAIN)


# Literal SQL for the same reason record_solve uses it: this runs once per
# solve, and building the statement cost more than executing it.
_BUMP_CELL = (
    "INSERT INTO solvebucket (bucket_start, user_id, captcha_type, count) VALUES (?, ?, ?, 1) "
    "ON CONFLICT (bucket_start, user_id, captcha_type) DO UPDATE SET count = count + 1"
)


def bump(conn, user_id: int, captcha_type: str, solved_at: int) -> None:
    """Add one solve to its cell. Takes a Connection; caller commits."""
    conn.exec_driver_sql(_BUMP_CELL, (bucket_of(solved_at), user_id, captcha_type))


def backfill(session) -> int:
    """Rebuild every cell from the last complete boundary forward.

    Resumable by construction: the newest cell in the rollup may be half
    filled (the app stopped mid-bucket, or ran a version that did not write
    rollups at all), so it is dropped and recomputed along with everything
    after it. Rows older than that boundary are already final.

    Returns the number of cells written. Safe to call on every startup; it is
    a no-op once the rollup has caught up.
    """
    frontier = session.execute(
        text("SELECT COALESCE(MAX(bucket_start), 0) FROM solvebucket")
    ).scalar_one()

    session.execute(
        text("DELETE FROM solvebucket WHERE bucket_start >= :frontier"),
        {"frontier": frontier},
    )
    written = session.execute(
        text(
            """
            INSERT INTO solvebucket (bucket_start, user_id, captcha_type, count)
            SELECT solved_at - (solved_at % :grain), user_id, captcha_type, COUNT(*)
            FROM solveevent
            WHERE solved_at >= :frontier
            GROUP BY 1, 2, 3
            """
        ),
        {"grain": GRAIN, "frontier": frontier},
    ).rowcount
    session.commit()
    return written
