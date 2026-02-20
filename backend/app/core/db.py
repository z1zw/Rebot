from __future__ import annotations

from typing import Any
import logging

from sqlmodel import SQLModel, Field, create_engine, Session, select

from app.core.settings import settings

logger = logging.getLogger(__name__)
_ENGINE: Any | None = None


class Execution(SQLModel, table=True):
    run_id: str = Field(primary_key=True)
    status: str = "pending"
    created_at: float
    updated_at: float
    result: str | None = None


def get_engine():
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE
    if not settings.database_url:
        return None
    try:
        _ENGINE = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # recover broken stale connections proactively
        )
    except Exception as exc:
        logger.warning("Failed to initialize database engine, falling back to memory-only mode: %s", exc)
        _ENGINE = None
    return _ENGINE


def init_db() -> None:
    engine = get_engine()
    if engine is None:
        return
    try:
        SQLModel.metadata.create_all(engine)
    except Exception as exc:
        logger.warning("init_db failed, backend will continue without DB persistence: %s", exc)


def upsert_execution(run_id: str, status: str, created_at: float, updated_at: float, result: str | None) -> None:
    engine = get_engine()
    if engine is None:
        return
    try:
        with Session(engine) as session:
            existing = session.get(Execution, run_id)
            if existing:
                existing.status = status
                existing.updated_at = updated_at
                existing.result = result
            else:
                session.add(
                    Execution(
                        run_id=run_id,
                        status=status,
                        created_at=created_at,
                        updated_at=updated_at,
                        result=result,
                    )
                )
            session.commit()
    except Exception as exc:
        logger.warning("upsert_execution failed (run_id=%s), keeping runtime state in memory only: %s", run_id, exc)


def get_execution(run_id: str) -> Execution | None:
    engine = get_engine()
    if engine is None:
        return None
    try:
        with Session(engine) as session:
            return session.get(Execution, run_id)
    except Exception as exc:
        logger.warning("get_execution failed (run_id=%s), fallback to memory store: %s", run_id, exc)
        return None
