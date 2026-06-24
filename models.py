from sqlmodel import Field, SQLModel
import time


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    # NOTE: counts are NOT stored here anymore. Every solve is a row in
    # SolveEvent, so per-captcha and total counts are derived (see
    # services/leaderboard_cache.py). That means adding a new captcha needs
    # zero schema changes.


class SolveEvent(SQLModel, table=True):
    # append-only history log. one row per solve, grows forever, never scanned
    # for the leaderboard (that's what SolveCount is for).
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    captcha_type: str = Field(index=True)  # matches a provider slug
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
