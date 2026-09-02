from fastapi import APIRouter, HTTPException, Request
from services.utils.get_ip import get_ip

from sqlmodel import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from models import User, SolveEvent, SolveCount
from database import SessionDep
from services.utils.cleandata import clean_data

#
from providers import CaptchaProvider, get_provider
from services.rollup import bump

import time


def record_solve(session: SessionDep, name: str, slug: str) -> None:
    """Log the solve: append history (SolveEvent) and bump the tally (SolveCount)."""
    user = session.exec(select(User).where(User.username == name)).first()
    if not user:
        # ratelimist here
        user = User(username=name)
        session.add(user)
        session.flush()  # assigns user.id for new users

    # one timestamp for both writes, so the event and its rollup cell can
    # never land in different buckets.
    solved_at = int(time.time())

    # append-only history
    session.add(SolveEvent(user_id=user.id, captcha_type=slug, solved_at=solved_at))

    # atomic "+1" tally: insert the row, or if it already exists, increment it.
    # done as a single UPSERT so two concurrent solves can't clobber each other.
    upsert = (
        sqlite_insert(SolveCount)
        .values(user_id=user.id, captcha_type=slug, count=1)
        .on_conflict_do_update(
            index_elements=["user_id", "captcha_type"],
            set_={"count": SolveCount.count + 1},
        )
    )
    session.execute(upsert)

    # the graphs read this, never the raw history
    bump(session, user.id, slug, solved_at)

    session.commit()
