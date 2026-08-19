# Changelog – FritzBox Home Assistant Integration

## [Unreleased]

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
