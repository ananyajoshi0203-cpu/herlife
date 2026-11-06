"""Per-person storage for the hosted web app: the app state blob and Oura tokens."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import DateTime, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

DB_URL = os.environ.get("BLOOM_WEB_DB", f"sqlite:///{Path(__file__).resolve().parents[2] / 'data' / 'bloom_web.db'}")


class Base(DeclarativeBase):
    pass


class AppState(Base):
    __tablename__ = "app_state"
    person_id: Mapped[str] = mapped_column(String, primary_key=True)
    state_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[int] = mapped_column()


class OuraToken(Base):
    __tablename__ = "oura_token"
    person_id: Mapped[str] = mapped_column(String, primary_key=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


engine = create_engine(DB_URL)
Base.metadata.create_all(engine)


def load_state(person_id: str) -> AppState | None:
    with Session(engine) as session:
        return session.get(AppState, person_id)


def save_state(person_id: str, state_json: str, updated_at: int) -> None:
    with Session(engine) as session:
        session.merge(AppState(person_id=person_id, state_json=state_json, updated_at=updated_at))
        session.commit()


def delete_person(person_id: str) -> None:
    with Session(engine) as session:
        for model in (AppState, OuraToken, GoogleToken):
            row = session.get(model, person_id)
            if row is not None:
                session.delete(row)
        session.commit()


def oura_token(person_id: str) -> OuraToken | None:
    with Session(engine) as session:
        return session.scalars(select(OuraToken).where(OuraToken.person_id == person_id)).first()


def save_oura_token(person_id: str, access_token: str, refresh_token: str | None, expires_at: datetime | None) -> None:
    with Session(engine) as session:
        session.merge(
            OuraToken(person_id=person_id, access_token=access_token, refresh_token=refresh_token, expires_at=expires_at)
        )
        session.commit()


def utcnow() -> datetime:
    return datetime.now(UTC)


class GoogleToken(Base):
    __tablename__ = "google_token"
    person_id: Mapped[str] = mapped_column(String, primary_key=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Base.metadata.create_all(engine)


def google_token(person_id: str) -> GoogleToken | None:
    with Session(engine) as session:
        return session.get(GoogleToken, person_id)


def save_google_token(person_id: str, access_token: str, refresh_token: str | None, expires_at: datetime | None) -> None:
    with Session(engine) as session:
        session.merge(
            GoogleToken(person_id=person_id, access_token=access_token, refresh_token=refresh_token, expires_at=expires_at)
        )
        session.commit()
