"""Database configuration; SQLite by default for zero-config college demo."""
import os
from pathlib import Path
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_URL = f"sqlite:///{ROOT / 'mood.db'}"


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    url = url or os.environ.get('MOOD_DATABASE_URL', DEFAULT_DB_URL)
    connect_args = {"check_same_thread": False} if url.startswith('sqlite:') else {}
    return create_engine(url, connect_args=connect_args)


def get_db(request: Request):
    with Session(request.app.state.engine) as session:
        yield session
