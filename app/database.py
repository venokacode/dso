from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DEFAULT_DB_URL = "sqlite:///./dso.db"


def resolve_db_url(explicit_db_url: str | None = None) -> str:
    if explicit_db_url:
        return explicit_db_url
    return os.getenv("DSO_DB_URL", DEFAULT_DB_URL)


def build_engine(db_url: str):
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    return create_engine(db_url, connect_args=connect_args, future=True)


def build_session_factory(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


Base = declarative_base()
