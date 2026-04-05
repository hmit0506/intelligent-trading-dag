"""
Exchange (Binance) time helpers.

Kline ``open_time`` / ``close_time`` from the API are UTC. YAML ``start_date`` / ``end_date``
are naive datetimes; interpret them in a configurable timezone, then convert to UTC for API
calls and for row filtering against UTC klines.

Timezone config may be:
- Fixed UTC offset: ``0``, ``+8``, ``-5``, ``UTC+8`` (integer hours; no DST).
- IANA name: ``Asia/Hong_Kong``, ``America/New_York`` (DST-aware where applicable).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from zoneinfo import ZoneInfo

# Whole-hour offsets only (matches user-facing "+N / -N").
_OFFSET_RE = re.compile(
    r"^\s*(?:UTC|GMT)?\s*([+-])(\d{1,2})\s*$",
    re.IGNORECASE,
)
_OFFSET_ONLY_RE = re.compile(r"^\s*([+-])(\d{1,2})\s*$")
_ZEROISH_RE = re.compile(
    r"^\s*(?:UTC|GMT)?\s*[-+]?\s*0\s*$",
    re.IGNORECASE,
)

_MAX_OFFSET_H = 14


def resolve_config_timezone(spec: Union[str, int]) -> datetime.tzinfo:
    """
    Build a ``datetime.tzinfo`` from a config ``timezone`` value.

    - ``0``, ``UTC``, ``GMT``, ``+0``, ``-0``, ``UTC+0`` → UTC
    - ``+8``, ``-5``, ``UTC+8`` → fixed offset (whole hours)
    - Otherwise → IANA ``ZoneInfo`` (e.g. ``Asia/Hong_Kong``)
    """
    if isinstance(spec, int) and not isinstance(spec, bool):
        if spec == 0:
            return timezone.utc
        if abs(spec) > _MAX_OFFSET_H:
            raise ValueError(
                f"UTC offset hours out of range (-{_MAX_OFFSET_H}..+{_MAX_OFFSET_H}): {spec!r}"
            )
        return timezone(timedelta(hours=spec))

    s = str(spec).strip()
    if not s:
        raise ValueError("timezone must be non-empty")

    if s.upper() in ("UTC", "GMT", "Z") or _ZEROISH_RE.match(s):
        return timezone.utc

    m = _OFFSET_RE.match(s) or _OFFSET_ONLY_RE.match(s)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        hours = sign * int(m.group(2))
        if abs(hours) > _MAX_OFFSET_H:
            raise ValueError(
                f"UTC offset hours out of range (-{_MAX_OFFSET_H}..+{_MAX_OFFSET_H}): {hours!r}"
            )
        return timezone(timedelta(hours=hours))

    try:
        return ZoneInfo(s)
    except Exception as e:
        raise ValueError(
            f"Invalid timezone {spec!r}. Use a fixed offset like 0, +8, -5, UTC+8, "
            f"or an IANA name (e.g. Asia/Hong_Kong)."
        ) from e


def validate_timezone_spec(value: Union[str, int]) -> str:
    """Validate and return a canonical string for storage (IANA or offset form)."""
    coerced = coerce_timezone_field(value)
    resolve_config_timezone(coerced)
    return coerced


def coerce_timezone_field(value: object) -> str:
    """
    Normalize YAML values: bare integers become "+8" / "-5" style strings for offsets.
    """
    if isinstance(value, int) and not isinstance(value, bool):
        if value == 0:
            return "UTC"
        if abs(value) > _MAX_OFFSET_H:
            raise ValueError(
                f"UTC offset hours out of range (-{_MAX_OFFSET_H}..+{_MAX_OFFSET_H}): {value!r}"
            )
        return f"{value:+d}"
    return str(value).strip()


def exchange_timestamp_ms(dt: datetime, tz_spec: Union[str, int] = "UTC") -> int:
    """
    Convert ``dt`` to Unix milliseconds for Binance API ``startTime`` / ``endTime``.

    Naive ``dt`` values are interpreted as wall time in ``tz_spec`` (offset or IANA).
    Aware ``dt`` values are converted to UTC.
    """
    if dt.tzinfo is not None:
        return int(dt.astimezone(timezone.utc).timestamp() * 1000)
    tz = resolve_config_timezone(tz_spec)
    utc = dt.replace(tzinfo=tz).astimezone(timezone.utc)
    return int(utc.timestamp() * 1000)


def naive_in_zone_to_utc_naive(dt: datetime, tz_spec: Union[str, int]) -> datetime:
    """
    Map naive clock time in ``tz_spec`` to naive UTC (same representation as Binance
    ``open_time`` in pandas without tz).
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    tz = resolve_config_timezone(tz_spec)
    return dt.replace(tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)


def format_utc_naive_for_display(dt: Any, tz_spec: Union[str, int]) -> str:
    """
    Format a Binance kline ``open_time`` / ``close_time`` value for logs.

    Stored values are **naive UTC** (no tz label). This converts to the user's
    ``timezone`` config (e.g. ``+8``) so a bar that opens at 16:00 UTC prints as
    ``00:00`` on the next calendar day in UTC+8.
    """
    if dt is None:
        return ""
    try:
        import pandas as pd

        if isinstance(dt, pd.Timestamp):
            if pd.isna(dt):
                return ""
            dt = dt.to_pydatetime()
    except ImportError:
        pass
    if not isinstance(dt, datetime):
        return str(dt)
    if dt.tzinfo is not None:
        utc_aware = dt.astimezone(timezone.utc)
    else:
        utc_aware = dt.replace(tzinfo=timezone.utc)
    local = utc_aware.astimezone(resolve_config_timezone(tz_spec))
    return local.strftime("%Y-%m-%d %H:%M:%S")
