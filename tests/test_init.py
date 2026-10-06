"""Tests for the config entry migration."""

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fritzbox import async_migrate_entry
from custom_components.fritzbox.const import DOMAIN


def _entry(host: str, minor_version: int = 1, version: int = 1, **extra):
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: host,
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
            **extra,
        },
        version=version,
        minor_version=minor_version,
    )


async def test_migrate_bare_host(hass: HomeAssistant) -> None:
    """A bare host becomes an http URL and verify_ssl is added."""
    entry = _entry("fritz.box")
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.data[CONF_HOST] == "http://fritz.box"
    assert entry.data[CONF_VERIFY_SSL] is True
    assert entry.data[CONF_USERNAME] == "admin"
    assert entry.data[CONF_PASSWORD] == "secret"
    assert (entry.version, entry.minor_version) == (1, 2)


async def test_migrate_keeps_url_and_existing_verify_ssl(hass: HomeAssistant) -> None:
    """A URL written by an older downgrade keeps scheme and verify_ssl."""
    entry = _entry("https://fritz.box:8443/", **{CONF_VERIFY_SSL: False})
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.data[CONF_HOST] == "https://fritz.box:8443"
    assert entry.data[CONF_VERIFY_SSL] is False
    assert entry.minor_version == 2


async def test_migrate_unparsable_host_is_kept(hass: HomeAssistant) -> None:
    """A host that cannot be turned into a URL does not break the migration."""
    entry = _entry("http://")
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.data[CONF_HOST] == "http://"
    assert entry.minor_version == 2


async def test_migrate_current_entry_is_untouched(hass: HomeAssistant) -> None:
    """An entry that is already 1.2 is not rewritten."""
    entry = _entry("http://fritz.box", minor_version=2, **{CONF_VERIFY_SSL: True})
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.data[CONF_HOST] == "http://fritz.box"
    assert entry.minor_version == 2


async def test_migrate_future_version_is_refused(hass: HomeAssistant) -> None:
    """Entries from a future major version are not migrated."""
    entry = _entry("fritz.box", version=2)
    entry.add_to_hass(hass)

    assert not await async_migrate_entry(hass, entry)
