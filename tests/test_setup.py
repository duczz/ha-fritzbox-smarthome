"""Tests for the setup of a config entry (migration, client, translations)."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

from pyfritzhome import LoginError
import pytest
from requests.exceptions import ConnectionError as RequestConnectionError

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fritzbox.const import DOMAIN


@pytest.fixture
def client() -> Generator[MagicMock]:
    """Patch the client of the coordinator with an empty FRITZ!Box."""
    with patch("custom_components.fritzbox.coordinator.Fritzhome") as mock_class:
        mock = mock_class.return_value
        mock.base_url = "http://fritz.box"
        mock.has_templates.return_value = False
        mock.has_triggers.return_value = False
        mock.get_devices.return_value = []
        yield mock_class


def _old_entry(**extra) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "fritz.box",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
            **extra,
        },
        version=1,
        minor_version=1,
    )


async def test_old_entry_is_migrated_and_set_up(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """A 1.1 entry (bare host) loads after migration and verifies SSL."""
    entry = _old_entry()
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.data[CONF_HOST] == "http://fritz.box"
    assert entry.data[CONF_VERIFY_SSL] is True
    kwargs = client.call_args.kwargs
    assert kwargs["host"] == "http://fritz.box"
    assert kwargs["ssl_verify"] is True


async def test_verify_ssl_false_reaches_client(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """The stored verify_ssl value is handed to pyfritzhome."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "https://fritz.box",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
            CONF_VERIFY_SSL: False,
        },
        version=1,
        minor_version=2,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    kwargs = client.call_args.kwargs
    assert kwargs["host"] == "https://fritz.box"
    assert kwargs["ssl_verify"] is False


async def test_entry_without_verify_ssl_still_loads(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """A 1.2 entry that lost verify_ssl (downgrade/reconfigure) falls back to True."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: "http://fritz.box",
            CONF_USERNAME: "admin",
            CONF_PASSWORD: "secret",
        },
        version=1,
        minor_version=2,
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)

    assert client.call_args.kwargs["ssl_verify"] is True


async def test_connection_error_is_translated(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """A connection error during setup is retried with a translated message."""
    client.return_value.login.side_effect = RequestConnectionError("boom")
    entry = _old_entry()
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert entry.error_reason_translation_key == "connect_error"
    assert entry.error_reason_translation_placeholders == {"error": "boom"}


async def test_login_error_starts_reauth(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """A wrong password ends in a translated error and a reauth flow."""
    client.return_value.login.side_effect = LoginError("admin")
    entry = _old_entry()
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert entry.error_reason_translation_key == "login_failed"
    assert any(
        flow["context"]["source"] == "reauth"
        for flow in hass.config_entries.flow.async_progress()
    )


async def test_obsolete_device_is_removed(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """A device the FRITZ!Box no longer reports is removed from the registry."""
    entry = _old_entry()
    entry.add_to_hass(hass)
    device_reg = dr.async_get(hass)
    gone = device_reg.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "00000 0000000")}
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert device_reg.async_get(gone.id) is None
