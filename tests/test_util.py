"""Tests for the URL helpers."""

import pytest

from custom_components.fritzbox.util import host_of, normalize_url


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("fritz.box", "http://fritz.box"),
        ("192.168.178.1", "http://192.168.178.1"),
        ("  http://fritz.box/  ", "http://fritz.box"),
        ("http://fritz.box", "http://fritz.box"),
        ("HTTPS://FRITZ.BOX:8443/some/path?x=1", "https://fritz.box:8443"),
        ("https://fritz.box:443", "https://fritz.box"),
        ("http://[fe80::1]", "http://[fe80::1]"),
    ],
)
def test_normalize_url(value: str, expected: str) -> None:
    """Bare hosts get http://, path and trailing slash are dropped."""
    assert normalize_url(value) == expected


@pytest.mark.parametrize(
    "value", ["", "http://", "ftp://fritz.box", "http:/fritz.box", "fritz box"]
)
def test_normalize_url_invalid(value: str) -> None:
    """Values without a usable http(s) host are rejected."""
    with pytest.raises(ValueError):
        normalize_url(value)


def test_host_of() -> None:
    """The host part is found for bare hosts and URLs alike."""
    assert host_of("fritz.box") == "fritz.box"
    assert host_of("https://192.168.178.1:8443") == "192.168.178.1"
    assert host_of("") is None
