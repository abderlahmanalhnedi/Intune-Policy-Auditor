"""SQLAlchemy database lifecycle and minimal persistent records."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, String, Text, create_engine, delete, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from intune_auditor.config import Settings


class Base(DeclarativeBase):
    pass


class AppSettingRecord(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)


def create_database_engine(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def apply_sqlite_safety(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    return engine


class Database:
    def __init__(self, settings: Settings) -> None:
        self.engine = create_database_engine(settings.database_path)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)
        with self.engine.connect() as connection:
            connection.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS idx_audit_records_created_at "
                "ON audit_records(created_at)"
            )
            connection.exec_driver_sql("PRAGMA optimize")

    def close(self) -> None:
        """Release pooled database connections during application or test shutdown."""
        self.engine.dispose()

    def session(self) -> Session:
        return self.session_factory()

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.session() as session:
            record = session.get(AppSettingRecord, key)
            return json.loads(record.value_json) if record is not None else default

    def set_setting(self, key: str, value: Any) -> None:
        serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
        with self.session() as session:
            record = session.get(AppSettingRecord, key)
            if record is None:
                record = AppSettingRecord(key=key, value_json=serialized)
                session.add(record)
            else:
                record.value_json = serialized
                record.updated_at = datetime.now(UTC)
            session.commit()

    def delete_setting(self, key: str) -> None:
        with self.session() as session:
            record = session.get(AppSettingRecord, key)
            if record is not None:
                session.delete(record)
                session.commit()

    def save_audit_summary(
        self,
        audit_id: str,
        created_at: datetime,
        expires_at: datetime,
        mode: str,
        summary: dict[str, Any],
    ) -> None:
        with self.session() as session:
            session.merge(
                AuditRecord(
                    id=audit_id,
                    created_at=created_at,
                    expires_at=expires_at,
                    mode=mode,
                    summary_json=json.dumps(summary, ensure_ascii=False, sort_keys=True),
                )
            )
            session.commit()

    def list_audit_summaries(self) -> list[dict[str, Any]]:
        with self.session() as session:
            records = session.scalars(
                select(AuditRecord).order_by(AuditRecord.created_at.desc())
            ).all()
            return [
                {
                    "audit_id": record.id,
                    "created_at": record.created_at.isoformat(),
                    "expires_at": record.expires_at.isoformat() if record.expires_at else None,
                    "mode": record.mode,
                    "summary": json.loads(record.summary_json),
                }
                for record in records
            ]

    def delete_expired_audits(self, now: datetime) -> int:
        with self.session() as session:
            identifiers = session.scalars(
                select(AuditRecord.id).where(
                    AuditRecord.expires_at.is_not(None), AuditRecord.expires_at <= now
                )
            ).all()
            session.execute(
                delete(AuditRecord).where(
                    AuditRecord.expires_at.is_not(None), AuditRecord.expires_at <= now
                )
            )
            session.commit()
            return len(identifiers)

    def clear_audits(self) -> int:
        with self.session() as session:
            identifiers = session.scalars(select(AuditRecord.id)).all()
            session.execute(delete(AuditRecord))
            session.commit()
            return len(identifiers)

    def reset_settings(self) -> int:
        with self.session() as session:
            identifiers = session.scalars(select(AppSettingRecord.key)).all()
            session.execute(delete(AppSettingRecord))
            session.commit()
            return len(identifiers)
