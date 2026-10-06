"""Tests for the FRITZ!SmartHome config flow."""

from unittest.mock import MagicMock

from pyfritzhome import LoginError
import pytest
from requests.exceptions import HTTPError, SSLError

from homeassistant.config_entries import SOURCE_SSDP, SOURCE_USER
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.ssdp import (
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_UDN,
    SsdpServiceInfo,
)

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.fritzbox.const import DOMAIN

USER_INPUT = {
    CONF_URL: "http://fritz.box/",
    CONF_USERNAME: "admin",
    CONF_PASSWORD: "secret",
    CONF_VERIFY_SSL: True,
}


def _entry(host: str, *, minor_version: int = 2, unique_id: str | None = None, **extra):
    data = {CONF_HOST: host, CONF_USERNAME: "admin", CONF_PASSWORD: "secret", **extra}
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=data,
        version=1,
        minor_version=minor_version,
        unique_id=unique_id,
    )
    return entry


def _ssdp(location: str, udn: str | None = "uuid:box-1") -> SsdpServiceInfo:
    upnp = {ATTR_UPNP_FRIENDLY_NAME: "FRITZ!Box 7490"}
    if udn:
        upnp[ATTR_UPNP_UDN] = udn
    return SsdpServiceInfo(
        ssdp_usn="",
        ssdp_st="urn:schemas-upnp-org:device:fritzbox:1",
        ssdp_location=location,
        upnp=upnp,
    )


async def _start_ssdp(hass: HomeAssistant, location: str, udn: str | None = "uuid:box-1"):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_SSDP}, data=_ssdp(location, udn)
    )


# --- user flow -------------------------------------------------------------


async def test_user_flow(
    hass: HomeAssistant, fritz: MagicMock, mock_setup_entry: MagicMock
) -> None:
    """The user flow stores a normalized URL and verify_ssl in a 1.2 entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_VERIFY_SSL: False}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "fritz.box"
    assert result["data"] == {
        CONF_HOST: "http://fritz.box",
        CONF_USERNAME: "admin",
        CONF_PASSWORD: "secret",
        CONF_VERIFY_SSL: False,
    }
    assert (result["result"].version, result["result"].minor_version) == (1, 2)


async def test_user_flow_passes_ssl_verify_to_client(
    hass: HomeAssistant, fritz: MagicMock, mock_setup_entry: MagicMock
) -> None:
    """The verify_ssl choice reaches the Fritzhome client."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {**USER_INPUT, CONF_URL: "https://fritz.box", CONF_VERIFY_SSL: False},
    )

    from custom_components.fritzbox import config_flow

    kwargs = config_flow.Fritzhome.call_args.kwargs
    assert kwargs["host"] == "https://fritz.box"
    assert kwargs["ssl_verify"] is False


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [(LoginError("admin"), "invalid_auth"), (SSLError(), "ssl_error")],
)
async def test_user_flow_retryable_errors(
    hass: HomeAssistant,
    fritz: MagicMock,
    mock_setup_entry: MagicMock,
    side_effect: Exception,
    error: str,
) -> None:
    """Wrong credentials and certificate errors are shown in the form."""
    fritz.login.side_effect = side_effect
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    # the user can fix the input and continue
    fritz.login.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("side_effect", "reason"),
    [(HTTPError(), "not_supported"), (OSError(), "no_devices_found")],
)
async def test_user_flow_aborting_errors(
    hass: HomeAssistant, fritz: MagicMock, side_effect: Exception, reason: str
) -> None:
    """Other connection problems abort the flow."""
    fritz.login.side_effect = side_effect
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == reason


async def test_user_flow_invalid_url(hass: HomeAssistant, fritz: MagicMock) -> None:
    """An address without a host is rejected."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_URL: "ftp://fritz.box"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}


@pytest.mark.parametrize("stored", ["fritz.box", "http://fritz.box", "http://fritz.box/"])
async def test_user_flow_duplicate(
    hass: HomeAssistant, fritz: MagicMock, stored: str
) -> None:
    """The same box is recognised whether stored as old host or as URL."""
    _entry(stored, minor_version=1).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# --- SSDP discovery ----------------------------------------------------------


async def test_ssdp_flow(
    hass: HomeAssistant, fritz: MagicMock, mock_setup_entry: MagicMock
) -> None:
    """A discovered box is set up with an http URL."""
    result = await _start_ssdp(hass, "http://192.168.178.1:49000/igddesc.xml")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: "admin", CONF_PASSWORD: "secret"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "FRITZ!Box 7490"
    assert result["data"][CONF_HOST] == "http://192.168.178.1"
    assert result["data"][CONF_VERIFY_SSL] is True
    assert result["result"].unique_id == "box-1"


async def test_ssdp_ignores_device_without_smarthome(
    hass: HomeAssistant, fritz: MagicMock
) -> None:
    """A device that definitely has no smarthome (e.g. repeater) is skipped."""
    fritz.has_smarthome_capabilities.return_value = False
    result = await _start_ssdp(hass, "http://192.168.178.2:49000/igddesc.xml")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_ssdp_continues_if_capabilities_unclear(
    hass: HomeAssistant, fritz: MagicMock
) -> None:
    """None means 'unknown' (very old firmware): discovery goes on."""
    fritz.has_smarthome_capabilities.return_value = None
    result = await _start_ssdp(hass, "http://192.168.178.2:49000/igddesc.xml")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"


async def test_ssdp_ipv6_url_is_bracketed(hass: HomeAssistant, fritz: MagicMock) -> None:
    """IPv6 hosts are put in brackets so the capability check can parse them."""
    from custom_components.fritzbox import config_flow

    result = await _start_ssdp(hass, "http://[2001:db8::1]:49000/igddesc.xml")
    assert result["type"] is FlowResultType.FORM
    assert config_flow.Fritzhome.call_args.kwargs["host"] == "http://[2001:db8::1]"


async def test_ssdp_ignores_link_local_ipv6(hass: HomeAssistant, fritz: MagicMock) -> None:
    """Link-local IPv6 addresses are not supported."""
    result = await _start_ssdp(hass, "http://[fe80::1]:49000/igddesc.xml")
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "ignore_ip6_link_local"


async def test_ssdp_hostname_instead_of_ip(hass: HomeAssistant, fritz: MagicMock) -> None:
    """A hostname in the SSDP location must not crash the flow (gotcha #19)."""
    result = await _start_ssdp(hass, "http://fritz.box:49000/igddesc.xml")
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"


async def test_ssdp_backfills_unique_id_of_old_entry(
    hass: HomeAssistant, fritz: MagicMock
) -> None:
    """An old entry (bare host, no unique_id) is recognised and gets the UDN."""
    entry = _entry("192.168.178.1", minor_version=1)
    entry.add_to_hass(hass)

    result = await _start_ssdp(hass, "http://192.168.178.1:49000/igddesc.xml")

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.unique_id == "box-1"


async def test_ssdp_backfills_unique_id_of_migrated_entry(
    hass: HomeAssistant, fritz: MagicMock
) -> None:
    """The same holds after migration, when the host is stored as URL."""
    entry = _entry("http://192.168.178.1")
    entry.add_to_hass(hass)

    result = await _start_ssdp(hass, "http://192.168.178.1:49000/igddesc.xml")

    assert result["reason"] == "already_configured"
    assert entry.unique_id == "box-1"


async def test_ssdp_follows_changed_ip_for_http_entry(
    hass: HomeAssistant, fritz: MagicMock
) -> None:
    """A known box that got a new IP is updated, scheme and port are kept."""
    entry = _entry("http://192.168.178.1:8080", unique_id="box-1")
    entry.add_to_hass(hass)

    result = await _start_ssdp(hass, "http://192.168.178.5:49000/igddesc.xml")

    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "http://192.168.178.5:8080"


async def test_ssdp_does_not_rewrite_https_entry(
    hass: HomeAssistant, fritz: MagicMock
) -> None:
    """An https entry keeps its host: an IP would break certificate checks."""
    entry = _entry("https://fritz.box", unique_id="box-1")
    entry.add_to_hass(hass)

    result = await _start_ssdp(hass, "http://192.168.178.5:49000/igddesc.xml")

    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == "https://fritz.box"


# --- reauth / reconfigure -----------------------------------------------------


async def test_reauth_heals_old_entry(
    hass: HomeAssistant, fritz: MagicMock, mock_setup_entry: MagicMock
) -> None:
    """Reauth of an entry without verify_ssl keeps working and completes it."""
    entry = _entry("fritz.box", minor_version=1)
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_USERNAME: "admin", CONF_PASSWORD: "new"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new"
    assert entry.data[CONF_VERIFY_SSL] is True
    # the reload after reauth runs the 1.1 -> 1.2 migration
    assert entry.data[CONF_HOST] == "http://fritz.box"
    assert entry.minor_version == 2


async def test_reconfigure(
    hass: HomeAssistant, fritz: MagicMock, mock_setup_entry: MagicMock
) -> None:
    """Reconfigure changes URL and verify_ssl and normalizes the URL."""
    entry = _entry("http://fritz.box", **{CONF_VERIFY_SSL: True})
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_URL: "https://fritz.box:443/", CONF_VERIFY_SSL: False},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == "https://fritz.box"
    assert entry.data[CONF_VERIFY_SSL] is False
    assert entry.data[CONF_PASSWORD] == "secret"


async def test_reconfigure_ssl_error_keeps_form(
    hass: HomeAssistant, fritz: MagicMock, mock_setup_entry: MagicMock
) -> None:
    """A certificate error shows up in the form and can be fixed."""
    entry = _entry("http://fritz.box", **{CONF_VERIFY_SSL: True})
    entry.add_to_hass(hass)
    fritz.login.side_effect = SSLError()

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "https://fritz.box", CONF_VERIFY_SSL: True}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "ssl_error"}

    fritz.login.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "https://fritz.box", CONF_VERIFY_SSL: False}
    )
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_VERIFY_SSL] is False


async def test_reconfigure_invalid_url_keeps_entry_name(
    hass: HomeAssistant, fritz: MagicMock, mock_setup_entry: MagicMock
) -> None:
    """After an input error the description still names the stored box."""
    entry = _entry("http://fritz.box", **{CONF_VERIFY_SSL: True})
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "ftp://fritz.box", CONF_VERIFY_SSL: True}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_url"}
    assert result["description_placeholders"] == {"name": "fritz.box"}
    assert entry.data[CONF_HOST] == "http://fritz.box"
