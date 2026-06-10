from sqlmodel import Field, SQLModel
import time


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    total_captchas_solved: int = Field(default=0, index=True)
    cloudflare_turnstiles_solved: int = Field(default=0, index=True)
    recaptcha_v2_solved: int = Field(
        default=0, index=True
    )  # DO NOT PUSH TO PROD ANY OF THIS


class SolveEvent(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    captcha_type: str = Field(index=True)
    solved_at: int = Field(
        index=True, default_factory=lambda: int(time.time())
    )  # Unix timestamps # apparently you can lambda it
