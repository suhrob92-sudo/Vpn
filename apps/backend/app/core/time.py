"""Datetime helpers.

Postgres (DateTime(timezone=True)) returns tz-aware values, SQLite (tests)
returns naive ones. All naive timestamps in this codebase are UTC by
construction, so coercing to UTC is always safe.
"""
from datetime import datetime, timezone


def aware_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
