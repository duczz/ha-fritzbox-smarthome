<div align="center">

# FRITZ!SmartHome

### A patched & improved FRITZ!SmartHome integration for Home Assistant

[![HACS Custom][hacs-badge]][hacs-url]
[![Home Assistant][ha-badge]][ha-url]
[![Version][version-badge]][release-url]
[![License][license-badge]](LICENSE)

[![Add to HACS][hacs-add-badge]][hacs-add-url]

</div>

---

This fork of the official Home Assistant [FRITZ!SmartHome integration][ha-url] fixes several upstream bugs and improves error handling and robustness across all platforms.

## 🔌 Supported Platforms

| Platform | Description |
|---|---|
| 🚨 `binary_sensor` | Alarm, window open, holiday/summer mode, battery low, lock state |
| 🔘 `button` | Apply FRITZ!SmartHome templates |
| 🌡️ `climate` | Control FRITZ!DECT thermostats (target temp, eco/comfort/boost/off) |
| 🪟 `cover` | Control FRITZ!DECT blinds and shutters |
| 💡 `light` | Control FRITZ!DECT smart bulbs (on/off, brightness, color, color temp) |
| 📊 `sensor` | Temperature, humidity, battery, power, voltage, current, energy, schedule |
| 🔁 `switch` | Smart plugs + FRITZ!SmartHome routines (triggers) |

<details>
<summary>📋 Sensor details</summary>

| Sensor | Unit | Device Class |
|---|---|---|
| Temperature | °C | `temperature` |
| Humidity | % | `humidity` |
| Battery level | % | `battery` |
| Power consumption | W | `power` |
| Voltage | V | `voltage` |
| Electric current | A | `current` |
| Total energy | kWh | `energy` |
| Comfort temperature | °C | `temperature` (diagnostic) |
| Eco temperature | °C | `temperature` (diagnostic) |
| Next scheduled temperature | °C | `temperature` (diagnostic) |
| Next schedule change time | — | `timestamp` (diagnostic) |
| Next scheduled preset | — | diagnostic |
| Current scheduled preset | — | diagnostic |

</details>

---

## 📦 Supported Devices

- FRITZ!DECT 200 / 210 — smart plugs with energy metering
- FRITZ!DECT 300 / 301 / 302 — thermostats
- FRITZ!DECT 400 / 440 — buttons and wall switches
- FRITZ!DECT 500 — smart bulb
- Comet DECT thermostat
- HAN-FUN devices (blinds, sensors, etc.)
- FRITZ!SmartHome templates and routines

---

## ✅ Requirements

- Home Assistant **2024.1.0** or newer
- A FRITZ!Box with FRITZ!SmartHome support
- **Smart Home** must be enabled in the FRITZ!Box UI

---

## 🚀 Installation

### HACS (recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations** → three-dot menu → **Custom repositories**
3. Add this repository URL, category: **Integration**
4. Search for **FRITZ!SmartHome** and install
5. Restart Home Assistant

### Manual

1. Copy all `.py`, `.json` files and the `translations/` folder into:
   ```
   <config>/custom_components/fritzbox/
   ```
2. Restart Home Assistant

---

## ⚙️ Configuration

**Settings → Devices & Services → Add Integration → FRITZ!SmartHome**

| Field | Description |
|---|---|
| Host | Hostname or IP (e.g. `fritz.box` or `192.168.178.1`) |
| Username | FRITZ!Box user account |
| Password | Password for the user account |
| SSL | Enable encrypted connection (optional) |

> **Tip:** Create a dedicated FRITZ!Box user with *Smart Home* permission only — do not use the admin account.

Auto-discovery via SSDP is supported. If your FRITZ!Box is on the local network, it may appear automatically.

---

## 🛠️ Improvements over the official integration

### 🐛 Bug Fixes

- **`coordinator.py`** — `UpdateFailed` now includes the original exception message instead of showing an empty error string in the HA UI
- **`coordinator.py`** — `HTTPError` (expired session) triggers an immediate re-login and retry so entities stay available without an ERROR log; if re-login fails with `LoginError` (password changed), a reauth flow is started automatically; `ConnectionError` and `TimeoutError` (e.g. nightly DSL forced reconnects) trigger a clean integration reload
- **`coordinator.py`** — `config_entry.title` is used as the coordinator name for readable log messages
- **`coordinator.py`** — Trigger entities are no longer incorrectly removed from the entity registry during cleanup
- **`cover.py`** — `async_set_cover_position` now triggers a coordinator refresh after the API call so the state updates immediately
- **`light.py`** — `hs_color` no longer crashes with a `TypeError` when a device returns `None` for hue or saturation
- **`climate.py`** — Missing `callback` import that caused a `NameError` when loading the platform is fixed
- **`__init__.py`** — `async_remove_config_entry_device` now correctly protects trigger devices from accidental removal

### ✨ Improvements

- **`diagnostics.py`** — FRITZ!SmartHome triggers (routines) are now included in diagnostic exports
- **`climate.py`** — Uses `_async_write_ha_state` (correct private method) for state updates

---

## 🤝 Contributing

Pull requests are welcome. For larger changes, please open an issue first to discuss your approach.

---

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=white
[hacs-url]: https://hacs.xyz
[ha-badge]: https://img.shields.io/badge/Home%20Assistant-2024.1+-41BDF5.svg?style=for-the-badge&logo=homeassistant&logoColor=white
[ha-url]: https://www.home-assistant.io/integrations/fritzbox
[version-badge]: https://img.shields.io/badge/version-1.0.4-22c55e.svg?style=for-the-badge&logo=github&logoColor=white
[release-url]: https://github.com/duczz/ha-fritzbox-smarthome/releases
[license-badge]: https://img.shields.io/badge/license-MIT-94a3b8.svg?style=for-the-badge
[hacs-add-badge]: https://my.home-assistant.io/badges/hacs_repository.svg
[hacs-add-url]: https://my.home-assistant.io/redirect/hacs_repository/?owner=duczz&repository=ha-fritzbox-smarthome&category=integration
