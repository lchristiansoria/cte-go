import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def build_database_url() -> str:
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit

    host = os.getenv("HOST_DB", "localhost")
    port = os.getenv("PORT_DB", "5432")
    name = os.getenv("NAME_DB", "cte_go")
    user = os.getenv("USR_DB", "postgres")
    password = os.getenv("PASS_DB", "postgres")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def create_engine_from_env(database_url: str | None = None, *, echo: bool = False) -> Engine:
    return create_engine(database_url or build_database_url(), echo=echo, future=True)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope(engine: Engine) -> Generator[Session, None, None]:
    session = get_session_factory(engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session(engine: Engine) -> Generator[Session, None, None]:
    session = get_session_factory(engine)()
    try:
        yield session
    finally:
        session.close()
