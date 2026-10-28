from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    # NOTE: captcha solve count is in the aptly named SolveCount. look below


# Here lies SolveEvent, from when we didn't have to worry about load
# There used to be a SolveEvent here: one append-only row per solve, the source
# both tables below were derived from. It was dropped at 51M rows / 2.2GB, which
# was the whole database, growing a million rows an hour at solver load. Nothing
# read it. The two aggregates say the same thing in 27k rows, and the writer
# maintains both in one transaction per batch, so they cannot drift apart.
#
# What that costs: these are primary data now, with nothing to rebuild them
# from. A writer bug is permanent rather than repairable.


class SolveCount(SQLModel, table=True):
    # running tally per (user, captcha). incremented on every solve so the
    # leaderboard reads ~ (#users * #captcha types) tiny rows instead of
    # counting solves. adding a new captcha = new rows, never a schema change.
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    captcha_type: str = Field(primary_key=True)  # matches a provider slug
    count: int = Field(default=0)


class SolveBucket(SQLModel, table=True):
    # 5-minute rollup, and the only thing the graphs read. Every row is the
    # count of solves in one (bucket, user, captcha) cell, bumped in the same
    # transaction as the tally above (see services/rollup.py). Coarser buckets
    # are derived by flooring bucket_start again, which is why the grain is the
    # finest one the graphs offer.
    bucket_start: int = Field(primary_key=True)  # unix ts floored to GRAIN
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    captcha_type: str = Field(primary_key=True)  # matches a provider slug
    count: int = Field(default=0)
