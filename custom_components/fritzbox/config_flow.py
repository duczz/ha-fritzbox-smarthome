"""Config flow for AVM FRITZ!SmartHome."""

from __future__ import annotations

from collections.abc import Mapping
import ipaddress
from typing import Any, Self
from urllib.parse import urlparse

from pyfritzhome import Fritzhome, LoginError
from requests.exceptions import HTTPError, SSLError
import voluptuous as vol
from yarl import URL

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.helpers.service_info.ssdp import (
    ATTR_UPNP_FRIENDLY_NAME,
    ATTR_UPNP_UDN,
    SsdpServiceInfo,
)

from .const import DEFAULT_URL, DEFAULT_USERNAME, DEFAULT_VERIFY_SSL, DOMAIN
from .util import host_of, normalize_url

URL_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))
PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

DATA_SCHEMA_USER = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): URL_SELECTOR,
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)

DATA_SCHEMA_CONFIRM = vol.Schema(
    {
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)

RESULT_INVALID_AUTH = "invalid_auth"
RESULT_INVALID_URL = "invalid_url"
RESULT_NO_DEVICES_FOUND = "no_devices_found"
RESULT_NOT_SUPPORTED = "not_supported"
RESULT_SSL_ERROR = "ssl_error"
RESULT_SUCCESS = "success"

# Results that are shown as a form error so the user can correct the input;
# every other failed result aborts the flow.
RETRYABLE_RESULTS = (RESULT_INVALID_AUTH, RESULT_SSL_ERROR)


class FritzboxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a AVM FRITZ!SmartHome config flow."""

    VERSION = 1
    MINOR_VERSION = 2

    _name: str

    def __init__(self) -> None:
        """Initialize flow."""
        self._url: str | None = None
        self._password: str | None = None
        self._username: str | None = None
        self._verify_ssl: bool = DEFAULT_VERIFY_SSL

    def _get_entry(self, name: str) -> ConfigFlowResult:
        return self.async_create_entry(
            title=name,
            data={
                CONF_HOST: self._url,
                CONF_PASSWORD: self._password,
                CONF_USERNAME: self._username,
                CONF_VERIFY_SSL: self._verify_ssl,
            },
        )

    def _url_is_configured(self, url: str) -> bool:
        """Return True if an entry for this URL exists (stored with or without scheme)."""
        for entry in self._async_current_entries(include_ignore=False):
            try:
                if normalize_url(entry.data[CONF_HOST]) == url:
                    return True
            except (KeyError, ValueError):
                continue
        return False

    async def async_try_connect(self) -> str:
        """Try to connect and check auth."""
        return await self.hass.async_add_executor_job(self._try_connect)

    def _try_connect(self) -> str:
        """Try to connect and check auth."""
        fritzbox = Fritzhome(
            host=self._url,
            user=self._username,
            password=self._password,
            ssl_verify=self._verify_ssl,
        )
        try:
            fritzbox.login()
            fritzbox.get_device_elements()
            fritzbox.logout()
        except LoginError:
            return RESULT_INVALID_AUTH
        except SSLError:
            return RESULT_SSL_ERROR
        except HTTPError:
            return RESULT_NOT_SUPPORTED
        except OSError:
            return RESULT_NO_DEVICES_FOUND
        return RESULT_SUCCESS

    async def async_has_smarthome_capabilities(self) -> bool | None:
        """Test if the device has smarthome capabilities (None if unclear)."""
        return await self.hass.async_add_executor_job(self._has_smarthome_capabilities)

    def _has_smarthome_capabilities(self) -> bool | None:
        """Test if the device has smarthome capabilities (None if unclear)."""
        fritzbox = Fritzhome(
            host=self._url, user=None, password=None, ssl_verify=False
        )
        return fritzbox.has_smarthome_capabilities()  # type: ignore[no-any-return]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            try:
                url = normalize_url(user_input[CONF_URL])
            except ValueError:
                errors["base"] = RESULT_INVALID_URL
            else:
                if self._url_is_configured(url):
                    return self.async_abort(reason="already_configured")

                self._url = url
                self._verify_ssl = user_input[CONF_VERIFY_SSL]
                self._name = host_of(url) or url
                self._password = user_input[CONF_PASSWORD]
                self._username = user_input[CONF_USERNAME]

                result = await self.async_try_connect()

                if result == RESULT_SUCCESS:
                    return self._get_entry(self._name)
                if result not in RETRYABLE_RESULTS:
                    return self.async_abort(reason=result)
                errors["base"] = result

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA_USER, errors=errors
        )

    def _discovery_updates(self, uuid: str, host: str) -> dict[str, str] | None:
        """Return the host update for an already known box, if one is safe.

        Only plain-http entries follow a changed address. Moving an https entry
        to the discovered IP would break certificate verification.
        """
        entry = self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, uuid)
        if entry is None:
            return None
        try:
            stored = URL(normalize_url(entry.data[CONF_HOST]))
        except (KeyError, ValueError):
            return None
        if stored.scheme != "http":
            return None
        return {CONF_HOST: str(stored.with_host(host).origin())}

    async def async_step_ssdp(
        self, discovery_info: SsdpServiceInfo
    ) -> ConfigFlowResult:
        """Handle a flow initialized by discovery."""
        host = urlparse(discovery_info.ssdp_location).hostname
        assert isinstance(host, str)

        try:
            ip = ipaddress.ip_address(host)
            if ip.version == 6 and ip.is_link_local:
                return self.async_abort(reason="ignore_ip6_link_local")
        except ValueError:
            pass

        if uuid := discovery_info.upnp.get(ATTR_UPNP_UDN):
            uuid = uuid.removeprefix("uuid:")
            await self.async_set_unique_id(uuid)
            self._abort_if_unique_id_configured(
                updates=self._discovery_updates(uuid, host)
            )

        self._url = str(URL.build(scheme="http", host=host))
        if self.hass.config_entries.flow.async_has_matching_flow(self):
            return self.async_abort(reason="already_in_progress")

        # update old and user-configured config entries
        for entry in self._async_current_entries(include_ignore=False):
            if host_of(entry.data.get(CONF_HOST, "")) == host.lower():
                if uuid and not entry.unique_id:
                    self.hass.config_entries.async_update_entry(entry, unique_id=uuid)
                return self.async_abort(reason="already_configured")

        # skip devices that definitely cannot control Smart Home devices
        # (e.g. repeaters); None means unclear, so discovery goes on
        if await self.async_has_smarthome_capabilities() is False:
            return self.async_abort(reason=RESULT_NOT_SUPPORTED)

        self._name = str(discovery_info.upnp.get(ATTR_UPNP_FRIENDLY_NAME) or host)

        self.context["title_placeholders"] = {"name": self._name}
        return await self.async_step_confirm()

    def is_matching(self, other_flow: Self) -> bool:
        """Return True if other_flow is matching this flow."""
        return other_flow._url == self._url  # noqa: SLF001

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle user-confirmation of discovered node."""
        errors = {}

        if user_input is not None:
            self._password = user_input[CONF_PASSWORD]
            self._username = user_input[CONF_USERNAME]
            result = await self.async_try_connect()

            if result == RESULT_SUCCESS:
                return self._get_entry(self._name)
            if result not in RETRYABLE_RESULTS:
                return self.async_abort(reason=result)
            errors["base"] = result

        return self.async_show_form(
            step_id="confirm",
            data_schema=DATA_SCHEMA_CONFIRM,
            description_placeholders={"name": self._name},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Trigger a reauthentication flow."""
        self._url = entry_data[CONF_HOST]
        self._verify_ssl = entry_data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        self._name = host_of(self._url) or str(self._url)
        self._username = entry_data[CONF_USERNAME]

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthorization flow."""
        errors = {}

        if user_input is not None:
            self._password = user_input[CONF_PASSWORD]
            self._username = user_input[CONF_USERNAME]

            result = await self.async_try_connect()

            if result == RESULT_SUCCESS:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={
                        CONF_HOST: self._url,
                        CONF_PASSWORD: self._password,
                        CONF_USERNAME: self._username,
                        CONF_VERIFY_SSL: self._verify_ssl,
                    },
                )
            if result not in RETRYABLE_RESULTS:
                return self.async_abort(reason=result)
            errors["base"] = result

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME, default=self._username): str,
                    vol.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
                }
            ),
            description_placeholders={"name": self._name},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        errors = {}
        reconfigure_entry = self._get_reconfigure_entry()
        url = reconfigure_entry.data[CONF_HOST]
        verify_ssl = reconfigure_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

        if user_input is not None:
            url = user_input[CONF_URL]
            verify_ssl = user_input[CONF_VERIFY_SSL]
            try:
                self._url = normalize_url(url)
            except ValueError:
                errors["base"] = RESULT_INVALID_URL
            else:
                self._verify_ssl = verify_ssl
                self._username = reconfigure_entry.data[CONF_USERNAME]
                self._password = reconfigure_entry.data[CONF_PASSWORD]

                result = await self.async_try_connect()

                if result == RESULT_SUCCESS:
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        data_updates={
                            CONF_HOST: self._url,
                            CONF_VERIFY_SSL: self._verify_ssl,
                        },
                    )
                errors["base"] = result

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_URL, default=url): URL_SELECTOR,
                    vol.Required(CONF_VERIFY_SSL, default=verify_ssl): bool,
                }
            ),
            description_placeholders={"name": host_of(url) or url},
            errors=errors,
        )
