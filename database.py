import os
from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import event

sqlite_file_name = os.getenv("DATABASE_PATH", "database.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, conn_record):
    # WAL = concurrent readers + a non-blocking writer (vs default's one-at-a-time
    # lock). synchronous=NORMAL is the standard, safe throughput companion to WAL.
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    # WAL still serialises writers, and sqlite's default is to give up the
    # instant one is busy. Wait instead of 500-ing a solve that was fine.
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

    # create_all never alters an existing table, so databases made before
    # User.username was unique still carry the plain index. Solves are recorded
    # off the event loop now, which means two threads can race to create the
    # same new user; the uniqueness is what turns that race into a no-op
    # instead of a duplicate row. Swap the index in place, idempotently.
    with engine.begin() as conn:
        existing = conn.exec_driver_sql(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='ix_user_username'"
        ).scalar()
        if existing and "UNIQUE" not in existing.upper():
            conn.exec_driver_sql("DROP INDEX ix_user_username")
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX ix_user_username ON user (username)"
            )


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
