# Changelog – FritzBox Home Assistant Integration

## [Unreleased]

### Features

#### `config_flow.py`, `__init__.py`, `coordinator.py` — URL based configuration with SSL verification
- **Change:** The FRITZ!Box is now configured by URL (`http://fritz.box`, `https://fritz.box:443`, ...) plus a *Verify SSL certificate* switch, in the setup, reauth and reconfigure steps. This adopts the upstream change (home-assistant/core #179839), but keeps `voluptuous` and the fork's SSDP handling.
- **Migration:** Config entries are migrated from 1.1 to 1.2 on the first start. A plain host such as `fritz.box` becomes `http://fritz.box`, `verify_ssl` is set to `true`. Entries that already hold a URL keep it. Entries without `verify_ssl` (for example after a downgrade) are read as `true`.
- **Discovery:** Known boxes are recognised whether the entry stores a plain host or a URL. A known `http://` box follows a changed IP address; an `https://` entry keeps its host, because an IP address would break the certificate check.
- **Errors:** A certificate problem is shown in the form (`ssl_error`) instead of aborting the flow, an invalid address as `invalid_url`.

#### `config_flow.py` — SSDP discovery skips devices without Smart Home
- **Change:** Adopted from upstream (home-assistant/core #183708): devices that definitely have no Smart Home capability (e.g. FRITZ!Repeater) abort the discovery with `not_supported`. If the check is inconclusive, discovery goes on. Requires `pyfritzhome` 0.6.21. The fork's guard for hostnames in the SSDP location is kept.

### Improvements

#### `coordinator.py` — translated exceptions
- **Change:** Adopted from upstream (home-assistant/core #170445): `connect_error`, `connect_error_reload` and `login_failed` are translated. The original error text stays part of the message (`{error}`), so the HTTP code or timeout is still visible.
- Field descriptions for username and password added (home-assistant/core #170219).

#### `coordinator.py` — device registry API
- **Change:** Obsolete devices are removed with `async_remove_device()` instead of `async_update_device(remove_config_entry_id=...)`, which Home Assistant Core deprecates (removal planned for 2027.8).

#### Housekeeping
- `pyfritzhome` 0.6.21.
- The minimum Home Assistant version in `hacs.json` and the README is now 2025.3.0. The old value (2024.1.0) was wrong; the code needs `AddConfigEntryEntitiesCallback` (2025.3.0) and `homeassistant.helpers.service_info.ssdp` (2025.2.0).
- Tests for the migration, the config flow and the setup (`tests/`, run with `pytest-homeassistant-custom-component` on Linux/WSL).
- `icons.json` added to the upstream sync check.

## [1.0.6] - 2026-08-19

### Bugfixes

#### `climate.py` — Missing `HomeAssistantError` import
- **Problem:** `check_active_or_lock_mode()` raises `HomeAssistantError` when a user tries to change temperature, HVAC mode, or preset while holiday/summer mode is active or the device is locked — but the class was never imported, causing a `NameError` instead of the intended translated message.
- **Fix:** Added `from homeassistant.exceptions import HomeAssistantError`.

#### `coordinator.py` — Read timeouts not detected
- **Problem:** The automatic-reload-on-timeout logic caught the builtin `TimeoutError`, which `requests.exceptions.ReadTimeout` (a slow-but-connected FRITZ!Box) never raises — only connection-level timeouts were actually caught.
- **Fix:** Also catch `requests.exceptions.Timeout`.

#### `coordinator.py` — `XMLParseError` not handled during runtime re-login
- **Problem:** A garbled XML response from the FRITZ!Box was only handled during the initial setup login, not during the silent re-login that follows a session expiry at runtime.
- **Fix:** Catch `XMLParseError` in the runtime re-login path too, triggering a clean reload instead of an unhandled error.

#### `coordinator.py` — `has_templates()` unguarded against `HTTPError`
- **Problem:** `has_triggers()` was guarded against `HTTPError` for old Fritz!OS versions without that endpoint; `has_templates()`, structurally identical, was not.
- **Fix:** Added the same guard to `has_templates()`.

#### `coordinator.py` — Power-meter zero-check could crash the whole poll cycle
- **Problem:** The powermeter-glitch check compared `device.energy <= 0` without first checking it was actually an `int` (unlike `voltage`/`power` in the same condition). If `energy` stayed `None`, this raised a `TypeError` that aborted the update cycle for all devices, not just the affected one.
- **Fix:** Added an `isinstance(device.energy, int)` guard.

#### `cover.py` — Missing `async_refresh()` after `set_position`
- **Problem:** `async_set_cover_position` didn't refresh the coordinator afterwards, unlike `open`/`close`/`stop` in the same file, so the position slider only updated on the next poll interval.
- **Fix:** Added `await self.coordinator.async_refresh()`.

#### `__init__.py` — Device-removal guard missed sub-unit-only devices
- **Problem:** Devices that report only a sub-unit without a separate main device (e.g. Energy 250, HA issue #145204) weren't matched by the removal guard's identifier check, so "Remove device" in the HA UI could succeed on a still-active device.
- **Fix:** Build the protected-AIN set from each known device's `device_and_unit_id[0]` instead of comparing against the raw AIN.

#### `entity.py` — Entity names frozen at creation
- **Problem:** Switch, cover, light, thermostat, and trigger entities set an explicit name once at creation time instead of using HA's `has_entity_name` convention, so renaming the device in Home Assistant had no effect on the entity name.
- **Fix:** Set `_attr_has_entity_name = True` unconditionally on the base entity class, matching upstream.

---

*Older notes describing a broader, never-implemented error-handling pass were removed from this file — they didn't reflect the actual codebase.*
