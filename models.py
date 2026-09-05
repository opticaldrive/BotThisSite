from sqlmodel import Field, SQLModel
import time


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    # NOTE: counts are NOT stored here anymore. Every solve is a row in
    # SolveEvent, so per-captcha and total counts are derived (see
    # services/leaderboard_cache.py). That means adding a new captcha needs
    # zero schema changes.


class SolveEvent(SQLModel, table=True):
    # append-only history log. one row per solve, grows forever, never scanned
    # for the leaderboard (that's what SolveCount is for).
    #
    # solved_at is the only indexed column, because backfill() is the only
    # thing that ever reads this table and it reads by time. Indexing user_id
    # or captcha_type as well cost two extra b-tree writes on every single
    # solve to answer queries nobody makes: measured at 8.5M rows, dropping
    # them took writes from 17.5k to 25.2k solves/s and the file from 593MB
    # to 347MB. Add one back the day a query actually needs it.
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    captcha_type: str = Field()  # matches a provider slug
    solved_at: int = Field(
        index=True, default_factory=lambda: int(time.time())
    )  # Unix timestamps # apparently you can lambda it


class SolveCount(SQLModel, table=True):
    # running tally per (user, captcha). incremented on every solve so the
    # leaderboard reads ~ (#users * #captcha types) tiny rows instead of
    # re-counting the whole SolveEvent table. adding a new captcha = new rows,
    # never a schema change.
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    captcha_type: str = Field(primary_key=True)  # matches a provider slug
    count: int = Field(default=0)


class SolveBucket(SQLModel, table=True):
    # 5-minute rollup of SolveEvent, and the only thing the graphs read. It is
    # a pure function of the history: every row is the count of events in one
    # (bucket, user, captcha) cell, so it can always be rebuilt from
    # SolveEvent (see services/rollup.py). Coarser buckets are derived by
    # flooring bucket_start again, which is why the grain is the finest one
    # the graphs offer.
    bucket_start: int = Field(primary_key=True)  # unix ts floored to GRAIN
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    captcha_type: str = Field(primary_key=True)  # matches a provider slug
    count: int = Field(default=0)
