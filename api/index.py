"""Vercel entry point: Vercel's Python runtime serves the ASGI `app` it finds here."""

from backend.webapp.server import app

__all__ = ["app"]
