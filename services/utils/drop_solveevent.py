"""Drop the solveevent table and reclaim its pages.

    uv run python services/utils/drop_solveevent.py --db /var/lib/botme/data/botme.db
    uv run python services/utils/drop_solveevent.py --db ... --vacuum

The app stopped writing solveevent; this removes what is already there. It is
a separate script rather than a startup migration because dropping 51M rows and
vacuuming 2.2GB is minutes of held write lock, and startup is exactly when the
solvers are queueing to write.

--vacuum is the half that actually returns disk to the filesystem. Without it
the pages go to the freelist and the file stays its old size (fine, and much
faster: new rows reuse them). With it sqlite writes a fresh copy of the whole
database beside the original, so the filesystem needs room for both for the
duration. Check that before reaching for it.

Take a backup first. This is not reversible: solvecount and solvebucket cannot
be recomputed once the history is gone.
"""

import argparse
import os
import sqlite3
import time


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", required=True, help="path to botme.db")
    ap.add_argument(
        "--vacuum",
        action="store_true",
        help="VACUUM afterwards to shrink the file (needs free space for a full copy)",
    )
    args = ap.parse_args()

    con = sqlite3.connect(args.db, timeout=60.0, isolation_level=None)
    con.execute("PRAGMA busy_timeout=60000")

    present = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='solveevent'"
    ).fetchone()
    if not present:
        print("solveevent is already gone; nothing to do")
        return 0

    rows = con.execute("SELECT COUNT(*) FROM solveevent").fetchone()[0]
    before = os.path.getsize(args.db)
    print(f"solveevent: {rows:,} rows, database {before / 1e9:.2f} GB")

    # Sanity: the aggregates are about to become the only copy. Refuse to run
    # if they look empty, because that is the one case where the history is
    # still load-bearing.
    buckets = con.execute("SELECT COUNT(*) FROM solvebucket").fetchone()[0]
    counts = con.execute("SELECT COUNT(*) FROM solvecount").fetchone()[0]
    print(f"solvebucket: {buckets:,} rows   solvecount: {counts:,} rows")
    if buckets == 0 or counts == 0:
        print("refusing: an aggregate is empty, so the history is still the only copy")
        return 1

    t0 = time.monotonic()
    con.execute("DROP TABLE solveevent")
    print(f"dropped in {time.monotonic() - t0:.1f}s")

    if args.vacuum:
        t0 = time.monotonic()
        con.execute("VACUUM")
        print(f"vacuumed in {time.monotonic() - t0:.1f}s")
    else:
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    con.close()
    after = os.path.getsize(args.db)
    print(f"database {before / 1e9:.2f} GB -> {after / 1e9:.2f} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
