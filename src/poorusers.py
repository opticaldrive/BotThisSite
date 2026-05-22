# code based on example from fastapi wesbsite
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    cloudflare_turnstiles_solved: int = Field(default=0)


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()


# https://ipv4.games/claim?name=whatever
@app.get("/claim")
def claim(name: str, session: SessionDep):
    # if usr hasnt spawned, spawn user
    user = User(username=name)
    statement = select(User).where(User.username == name)  # uh
    user = session.exec(statement).first()

    if not user:  # then user not existy
        user = User(username=name)
        session.add(user)

    user.cloudflare_turnstiles_solved += 1
    print("did it add")
    session.add(user)
    session.commit()
    session.refresh(user)
    # yay we refreshed user
    return user
