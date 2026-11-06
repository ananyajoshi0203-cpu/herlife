"""Google Calendar for the hosted web app: OAuth, today's events, and creating a booked session."""

from __future__ import annotations

import os
import urllib.parse
from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
SCOPE = "https://www.googleapis.com/auth/calendar.events"
TIMEOUT = timedelta(seconds=15)
EXPIRY_MARGIN = timedelta(minutes=2)
DEFAULT_REDIRECT_URI = "http://localhost:8080/google/callback"


class GoogleNotConfigured(RuntimeError):
    pass


class GoogleClientConfig(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str

    @classmethod
    def from_env(cls) -> GoogleClientConfig:
        client_id, client_secret = os.environ.get("GOOGLE_CLIENT_ID"), os.environ.get("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise GoogleNotConfigured("Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to connect Google Calendar.")
        return cls(client_id=client_id, client_secret=client_secret,
                   redirect_uri=os.environ.get("GOOGLE_REDIRECT_URI", DEFAULT_REDIRECT_URI))


class GoogleTokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None

    def expires_at(self, now: datetime) -> datetime | None:
        return now + timedelta(seconds=self.expires_in) if self.expires_in is not None else None


class CalendarEvent(BaseModel):
    title: str
    start: datetime
    end: datetime


class NewEvent(BaseModel):
    title: str
    start: datetime
    end: datetime


def authorize_url(config: GoogleClientConfig, state: str) -> str:
    # offline + consent so Google returns a refresh token on the first connect.
    query = urllib.parse.urlencode({
        "response_type": "code", "client_id": config.client_id, "redirect_uri": config.redirect_uri,
        "scope": SCOPE, "state": state, "access_type": "offline", "prompt": "consent",
    })
    return f"{AUTHORIZE_URL}?{query}"


def request_token(config: GoogleClientConfig, grant: dict[str, str]) -> GoogleTokenResponse:
    response = httpx.post(TOKEN_URL, data={**grant, "client_id": config.client_id, "client_secret": config.client_secret},
                          timeout=TIMEOUT.total_seconds())
    response.raise_for_status()
    return GoogleTokenResponse.model_validate_json(response.content)


def exchange_code(config: GoogleClientConfig, code: str) -> GoogleTokenResponse:
    return request_token(config, {"grant_type": "authorization_code", "code": code, "redirect_uri": config.redirect_uri})


def refresh(config: GoogleClientConfig, refresh_token: str) -> GoogleTokenResponse:
    return request_token(config, {"grant_type": "refresh_token", "refresh_token": refresh_token})


def needs_refresh(expires_at: datetime | None, now: datetime) -> bool:
    return expires_at is not None and expires_at - EXPIRY_MARGIN <= now


def events_between(access_token: str, start: datetime, end: datetime) -> list[CalendarEvent]:
    response = httpx.get(
        EVENTS_URL,
        params={"timeMin": start.isoformat(), "timeMax": end.isoformat(), "singleEvents": "true", "orderBy": "startTime"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=TIMEOUT.total_seconds(),
    )
    response.raise_for_status()
    events: list[CalendarEvent] = []
    for item in response.json().get("items", []):
        start_at, end_at = item.get("start", {}).get("dateTime"), item.get("end", {}).get("dateTime")
        if start_at and end_at:  # all-day events have no time slot to plan around
            events.append(CalendarEvent(title=item.get("summary") or "Busy", start=start_at, end=end_at))
    return events


def create_event(access_token: str, event: NewEvent) -> CalendarEvent:
    response = httpx.post(
        EVENTS_URL,
        json={"summary": event.title, "description": "Booked by Bloom from your plan for today.",
              "start": {"dateTime": event.start.isoformat()}, "end": {"dateTime": event.end.isoformat()}},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=TIMEOUT.total_seconds(),
    )
    response.raise_for_status()
    created = response.json()
    return CalendarEvent(title=created.get("summary", event.title), start=created["start"]["dateTime"], end=created["end"]["dateTime"])
