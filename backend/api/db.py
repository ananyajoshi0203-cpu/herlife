"""SQLite persistence for the API, via SQLAlchemy 2.0.

Wearable rows keep their canonical pydantic dump in `payload` and are validated
back into the canonical models on read, so adding a wearable or a canonical
field never needs a migration here.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{ROOT / 'data' / 'bloom_api.db'}"


class Base(DeclarativeBase):
    pass


class UserRow(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer)
    gym_access: Mapped[str] = mapped_column(String)
    diet: Mapped[list[str]] = mapped_column(JSON)
    conditions: Mapped[list[str]] = mapped_column(JSON)
    life_stage: Mapped[str] = mapped_column(String)
    goals: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class OuraTokenRow(Base):
    __tablename__ = "oura_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)


class OAuthStateRow(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class WearableDayRow(Base):
    __tablename__ = "wearable_days"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String, primary_key=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)


class PeriodRow(Base):
    __tablename__ = "periods"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    start_day: Mapped[date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String, primary_key=True)
    end_day: Mapped[date | None] = mapped_column(Date)
    flow: Mapped[str] = mapped_column(String)


class SelfReportRow(Base):
    __tablename__ = "self_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text)
    detail: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class HabitRow(Base):
    __tablename__ = "habits"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    why: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(Text)
    created_on: Mapped[date] = mapped_column(Date)


class HabitCheckRow(Base):
    __tablename__ = "habit_checks"

    habit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("habits.id"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)


class CheckinRow(Base):
    """A morning self check-in, the record's source when she has no wearable."""

    __tablename__ = "checkins"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    sleep_hours: Mapped[float] = mapped_column(Float)
    energy: Mapped[int] = mapped_column(Integer)
    stress: Mapped[int] = mapped_column(Integer)


class Database:
    def __init__(self, url: str = DEFAULT_DATABASE_URL) -> None:
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(url)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    def session(self) -> Iterator[Session]:
        with self.session_factory() as session:
            yield session
