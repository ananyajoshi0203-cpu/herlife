"""Oura OAuth2 authorization code flow: authorize URL, code exchange, refresh."""

from __future__ import annotations

import os
import urllib.parse
from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel

AUTHORIZE_URL = "https://cloud.ouraring.com/oauth/authorize"
TOKEN_URL = "https://api.ouraring.com/oauth/token"
SCOPES = ("daily", "heartrate", "personal")
DEFAULT_REDIRECT_URI = "http://localhost:8000/oura/callback"
TIMEOUT = timedelta(seconds=20)
# Refresh a little early so a token cannot expire between the check and the sync's last request.
EXPIRY_MARGIN = timedelta(minutes=5)


class OuraNotConfigured(RuntimeError):
    pass


class OuraClientConfig(BaseModel):
    client_id: str
    client_secret: str
    redirect_uri: str

    @classmethod
    def from_env(cls) -> OuraClientConfig:
        client_id, client_secret = os.environ.get("OURA_CLIENT_ID"), os.environ.get("OURA_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise OuraNotConfigured("Set OURA_CLIENT_ID and OURA_CLIENT_SECRET to connect Oura.")
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=os.environ.get("OURA_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None

    def expires_at(self, now: datetime) -> datetime | None:
        return now + timedelta(seconds=self.expires_in) if self.expires_in is not None else None


def authorize_url(config: OuraClientConfig, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": config.redirect_uri,
            "scope": " ".join(SCOPES),
            "state": state,
        }
    )
    return f"{AUTHORIZE_URL}?{query}"


def request_token(config: OuraClientConfig, grant: dict[str, str]) -> TokenResponse:
    response = httpx.post(
        TOKEN_URL,
        data={**grant, "client_id": config.client_id, "client_secret": config.client_secret},
        timeout=TIMEOUT.total_seconds(),
    )
    response.raise_for_status()
    return TokenResponse.model_validate_json(response.content)


def exchange_code(config: OuraClientConfig, code: str) -> TokenResponse:
    return request_token(
        config, {"grant_type": "authorization_code", "code": code, "redirect_uri": config.redirect_uri}
    )


def refresh(config: OuraClientConfig, refresh_token: str) -> TokenResponse:
    return request_token(config, {"grant_type": "refresh_token", "refresh_token": refresh_token})


def needs_refresh(expires_at: datetime | None, now: datetime) -> bool:
    return expires_at is not None and expires_at - EXPIRY_MARGIN <= now
