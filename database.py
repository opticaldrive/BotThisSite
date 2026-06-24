from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import event

sqlite_file_name = "database.db"
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
    cur.close()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
