#!/usr/bin/env python
"""
One-time production migration: pre-refactor schema  ->  registry + SolveCount.

Run on the box that has prod's database.db:

    uv run python migrate_prod.py                # migrate ./database.db
    uv run python migrate_prod.py path/to.db     # migrate a specific file
    uv run python migrate_prod.py --synthesize-history   # also backfill SolveEvent

What prod looks like (commit e6b2d9aa...):
    user(id, username, cloudflare_turnstiles_solved)   # counts live HERE
    -- there is NO solveevent table at that commit --

What we migrate to:
    user(id, username)                                 # count columns dropped
    solvecount(user_id, captcha_type, count)           # NEW running tally
    solveevent(id, user_id, captcha_type, solved_at)   # NEW append-only log

Historical data:
    The per-captcha counts (cloudflare_turnstiles_solved, ...) ARE the history,
    so they are copied verbatim into SolveCount -> nothing is lost, the
    leaderboard numbers stay identical.

    There is no per-solve history in prod (no solveevent rows existed), and we
    will NOT invent fake timestamps by default -- SolveEvent simply starts
    logging from migration day forward. If you'd rather have one placeholder
    SolveEvent row per historical solve (all stamped at migration time, so any
    event-derived stats reconcile), pass --synthesize-history.

Safety:
    * makes a timestamped backup of the db file first
    * runs inside a single transaction (all-or-nothing)
    * idempotent: re-running a migrated db is a no-op
"""

import argparse
import shutil
import sqlite3
import sys
import time

# old per-captcha count columns  ->  provider slug (see providers.py).
# only columns that actually exist in the table are used, so this works for the
# e6b2d9a schema (just cloudflare) and any later one.
COLUMN_TO_SLUG = {
    "cloudflare_turnstiles_solved": "cf-turnstile",
    "recaptcha_v2_solved": "recaptcha-v2",
}
# columns that are derived/aggregate, not a real captcha -> ignore them
IGNORE_COLUMNS = {"id", "username", "total_captchas_solved"}


def columns_of(con, table):
    return [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]


def table_exists(con, table):
    return (
        con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def main():
    ap = argparse.ArgumentParser(description="Migrate BotThisSite prod DB.")
    ap.add_argument("db", nargs="?", default="database.db", help="path to database.db")
    ap.add_argument(
        "--synthesize-history",
        action="store_true",
        help="backfill placeholder SolveEvent rows (stamped at migration time)",
    )
    args = ap.parse_args()

    user_cols = None
    con = sqlite3.connect(args.db)
    try:
        if not table_exists(con, "user"):
            sys.exit(f"no 'user' table in {args.db!r} -- is this the right database?")

        user_cols = columns_of(con, "user")
        count_cols = [
            c for c in user_cols if c in COLUMN_TO_SLUG and c not in IGNORE_COLUMNS
        ]

        # ---- idempotency: nothing to do if already migrated ----
        if not count_cols:
            print(
                "user table has no old count columns -- already migrated. "
                "Nothing to do."
            )
            # still make sure the new tables exist (harmless if they do)
            ensure_new_tables(con)
            con.commit()
            return
    finally:
        con.close()

    # ---- backup before touching anything ----
    backup = f"{args.db}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(args.db, backup)
    print(f"backed up {args.db} -> {backup}")

    now = int(time.time())
    con = sqlite3.connect(args.db)
    con.execute("PRAGMA foreign_keys=OFF")
    try:
        cur = con.cursor()
        cur.execute("BEGIN")

        ensure_new_tables(con)

        # ---- 1. compute final per-(user, captcha) counts ----
        # base: the authoritative old count columns
        # build: {(user_id, slug): count}
        counts: dict[tuple[int, str], int] = {}
        select_cols = ", ".join(["id"] + count_cols)
        for row in cur.execute(f"SELECT {select_cols} FROM user").fetchall():
            uid = row[0]
            for col, val in zip(count_cols, row[1:]):
                if val:  # skip zeros
                    counts[(uid, COLUMN_TO_SLUG[col])] = int(val)

        # merge in any pre-existing solveevent history (dev DBs may have it);
        # take the max so we never undercount a solve.
        if table_exists(con, "solveevent"):
            for uid, ctype, c in cur.execute(
                "SELECT user_id, captcha_type, COUNT(*) "
                "FROM solveevent GROUP BY user_id, captcha_type"
            ).fetchall():
                key = (uid, ctype)
                counts[key] = max(counts.get(key, 0), c)

        # ---- 2. write SolveCount (replace so re-runs are clean) ----
        cur.executemany(
            "INSERT INTO solvecount (user_id, captcha_type, count) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id, captcha_type) DO UPDATE SET count=excluded.count",
            [(uid, slug, c) for (uid, slug), c in counts.items()],
        )

        # ---- 2b. optional: synthesize placeholder history ----
        synthesized = 0
        if args.synthesize_history:
            existing = {
                (uid, ctype)
                for uid, ctype in cur.execute(
                    "SELECT DISTINCT user_id, captcha_type FROM solveevent"
                ).fetchall()
            }
            to_add = []
            for (uid, slug), c in counts.items():
                if (uid, slug) in existing:
                    continue  # already have real events for this pair
                to_add.extend((uid, slug, now) for _ in range(c))
            cur.executemany(
                "INSERT INTO solveevent (user_id, captcha_type, solved_at) "
                "VALUES (?, ?, ?)",
                to_add,
            )
            synthesized = len(to_add)

        # ---- 3. drop old count columns by rebuilding the user table ----
        cur.execute(
            "CREATE TABLE user_new (id INTEGER NOT NULL, username VARCHAR NOT NULL, "
            "PRIMARY KEY (id))"
        )
        cur.execute("INSERT INTO user_new (id, username) SELECT id, username FROM user")
        cur.execute("DROP TABLE user")
        cur.execute("ALTER TABLE user_new RENAME TO user")
        cur.execute("CREATE INDEX ix_user_username ON user (username)")

        con.commit()
    except Exception:
        con.rollback()
        print(f"migration FAILED and was rolled back. db restored; backup at {backup}")
        raise
    finally:
        con.execute("PRAGMA foreign_keys=ON")

    # ---- report + sanity check ----
    total = sum(counts.values())
    print(f"migrated {len(counts)} (user, captcha) tallies, {total} total solves")
    if args.synthesize_history:
        print(f"synthesized {synthesized} placeholder SolveEvent rows @ {now}")
    verify(args.db, total)
    print("done. drop the old backup once you've confirmed the site looks right.")


def ensure_new_tables(con):
    con.execute(
        "CREATE TABLE IF NOT EXISTS solvecount ("
        "user_id INTEGER NOT NULL, captcha_type VARCHAR NOT NULL, "
        "count INTEGER NOT NULL, PRIMARY KEY (user_id, captcha_type), "
        "FOREIGN KEY(user_id) REFERENCES user (id))"
    )
    con.execute(
        "CREATE TABLE IF NOT EXISTS solveevent ("
        "id INTEGER NOT NULL, user_id INTEGER NOT NULL, "
        "captcha_type VARCHAR NOT NULL, solved_at INTEGER NOT NULL, "
        "PRIMARY KEY (id), FOREIGN KEY(user_id) REFERENCES user (id))"
    )
    for stmt in (
        "CREATE INDEX IF NOT EXISTS ix_solveevent_user_id ON solveevent (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_solveevent_captcha_type ON solveevent (captcha_type)",
        "CREATE INDEX IF NOT EXISTS ix_solveevent_solved_at ON solveevent (solved_at)",
    ):
        con.execute(stmt)


def verify(db, expected_total):
    con = sqlite3.connect(db)
    try:
        got = con.execute("SELECT COALESCE(SUM(count), 0) FROM solvecount").fetchone()[0]
        remaining = [
            c for c in columns_of(con, "user") if c in COLUMN_TO_SLUG
        ]
        ok = got == expected_total and not remaining
        print(
            f"verify: SolveCount total={got} (expected {expected_total}); "
            f"old columns remaining={remaining or 'none'} -> "
            f"{'OK' if ok else 'MISMATCH!'}"
        )
        if not ok:
            sys.exit("verification failed -- inspect the backup before proceeding")
    finally:
        con.close()


if __name__ == "__main__":
    main()
