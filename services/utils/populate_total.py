# uv run python -m services.utils.populate_total
from sqlmodel import select, desc, func, Session
from models import User
from database import engine

with Session(engine) as session:
    users = session.exec(select(User)).all()
    for user in users:
        user.total_captchas_solved = (
            user.cloudflare_turnstiles_solved + user.recaptcha_v2_solved
        )
        session.add(user)
    session.commit()
