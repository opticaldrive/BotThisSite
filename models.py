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
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    captcha_type: str = Field(index=True)  # matches a provider slug
    solved_at: int = Field(
        index=True, default_factory=lambda: int(time.time())
    )  # Unix timestamps # apparently you can lambda it
