"""Helpers for the AVM FRITZ!SmartHome integration."""

from __future__ import annotations

from yarl import URL


def normalize_url(value: str) -> str:
    """Return the FRITZ!Box address as ``scheme://host[:port]``.

    A bare host or IP gets ``http://`` prepended; path, query and a trailing
    slash are dropped. Raises ValueError if no host can be determined.
    """
    value = value.strip()
    if any(char.isspace() for char in value) or (
        ":/" in value and "://" not in value
    ):
        raise ValueError(f"Invalid FRITZ!Box address: {value}")
    if "://" not in value:
        value = f"http://{value}"
    url = URL(value)
    if not url.host or url.scheme not in ("http", "https"):
        raise ValueError(f"Invalid FRITZ!Box address: {value}")
    return str(url.origin())


def host_of(value: str) -> str | None:
    """Return the host part of a stored host value (bare host or URL)."""
    try:
        return URL(normalize_url(value)).host
    except ValueError:
        return None
