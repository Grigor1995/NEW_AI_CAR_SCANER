from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session as DbSession, mapped_column

from diagnostic.models import DiagnosticSession
from diagnostic.database import database_engine

log = logging.getLogger(__name__)


class SessionStateBase(DeclarativeBase):
    pass


class DiagnosticSessionStateRow(SessionStateBase):
    __tablename__ = "diagnostic_session_state"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class DiagnosticSessionPersistence:
    """Shared persistence for Android, Desktop and iOS clients through the API.

    The API keeps the domain model in memory for fast deterministic reasoning,
    while persisting a complete DiagnosticSession snapshot to the configured
    DATABASE_URL. With Docker this is the shared PostgreSQL database.
    Without DATABASE_URL the existing in-memory development mode is retained.
    """

    def __init__(self) -> None:
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.enabled = bool(self.database_url)
        self.engine = None
        if not self.enabled:
            return

        self.engine = database_engine(self.database_url)
        try:
            SessionStateBase.metadata.create_all(self.engine)
        except Exception as exc:
            self.engine.dispose()
            raise RuntimeError(
                "Configured DATABASE_URL is unavailable. Start the database service or, "
                "for Desktop local storage, set AI_CAR_USE_LOCAL_DATABASE=1. "
                "No fallback database was selected and no existing data was moved."
            ) from exc

    def close(self) -> None:
        """Dispose the connection pool owned by this persistence instance."""
        engine = self.engine
        self.engine = None
        if engine is not None:
            engine.dispose()

    def load(self) -> dict[str, DiagnosticSession]:
        if not self.enabled or self.engine is None:
            return {}

        loaded: dict[str, DiagnosticSession] = {}
        try:
            with DbSession(self.engine) as db:
                rows = db.scalars(select(DiagnosticSessionStateRow)).all()
                for row in rows:
                    try:
                        session = DiagnosticSession.model_validate(row.payload)
                    except Exception:
                        log.exception("Skipping invalid persisted session %s", row.session_id)
                        continue
                    loaded[row.session_id] = session
        except Exception:
            log.exception("Failed to load persisted diagnostic sessions")
        return loaded

    def save_one(self, session_id: str, session: DiagnosticSession) -> None:
        """Persist one session immediately for cross-process/client visibility."""
        if not self.enabled or self.engine is None:
            return
        with DbSession(self.engine) as db:
            payload = session.model_dump(mode="json")
            row = db.get(DiagnosticSessionStateRow, session_id)
            if row is None:
                db.add(DiagnosticSessionStateRow(session_id=session_id, payload=payload))
            else:
                row.payload = payload
                row.updated_at = datetime.now(timezone.utc)
            db.commit()

    def save_all(self, sessions: dict[str, DiagnosticSession]) -> None:
        if not self.enabled or self.engine is None:
            return

        try:
            with DbSession(self.engine) as db:
                for session_id, session in sessions.items():
                    payload = session.model_dump(mode="json")
                    row = db.get(DiagnosticSessionStateRow, session_id)
                    if row is None:
                        row = DiagnosticSessionStateRow(
                            session_id=session_id,
                            payload=payload,
                        )
                        db.add(row)
                    else:
                        row.payload = payload
                        row.updated_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            log.exception("Failed to persist diagnostic sessions")


persistence = DiagnosticSessionPersistence()
