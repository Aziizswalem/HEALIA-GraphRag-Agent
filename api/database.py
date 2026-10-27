"""SQLAlchemy engine, session factory, and Base."""
from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config.settings import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionFactory = None


def _get_engine():
    global _engine
    if _engine is not None:
        return _engine
    s = get_settings()
    url = (s.DATABASE_URL or "").strip()
    if not url:
        db_dir = Path.cwd() / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{db_dir / 'healio.db'}"
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    _engine = create_engine(url, connect_args=connect_args, echo=False)
    # Import models to register them with Base.metadata before create_all
    import models  # noqa: F401
    Base.metadata.create_all(_engine)
    return _engine


def _get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is not None:
        return _SessionFactory
    _SessionFactory = sessionmaker(bind=_get_engine())
    return _SessionFactory


@contextmanager
def get_db() -> Generator[Session, None, None]:
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
