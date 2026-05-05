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

This fork of the official Home Assistant [FRITZ!SmartHome integration][ha-url] fixes several upstream bugs that affect reliability in real-world use — including session handling, connection recovery, and edge-case device states.

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

- **No ERROR log on session expiry** — When a FRITZ!Box session expires (HTTP 403), the integration re-authenticates and retries the update silently. No ERROR entry appears in the HA log unless the re-login itself fails. The official integration simply reloads on every 403 — causing a brief unavailability each time. (`coordinator.py`)

- **Automatic reauth on password change** — If the FRITZ!Box password changes, HA automatically starts a reauth flow instead of leaving the integration in a silent error state. (`coordinator.py`)

- **Automatic reload on connection loss** — A `ConnectionError` or `TimeoutError` (e.g. during nightly DSL forced reconnects) triggers a clean integration reload so the session is properly re-established. (`coordinator.py`)

- **Readable error messages in the HA UI** — Connection errors now include the original exception message (e.g. `Connection refused`) in the HA UI instead of showing an empty error string. (`coordinator.py`)

- **Trigger entities are preserved during cleanup** — FRITZ!SmartHome routines (triggers) are no longer incorrectly removed from the entity registry during device cleanup. The official integration loses trigger entities whenever the device list changes. (`coordinator.py`, `__init__.py`)

- **Trigger devices protected from accidental removal** — FRITZ!SmartHome routine devices can no longer be accidentally removed via the HA device registry UI. (`__init__.py`)

- **Cover position updates immediately** — After setting a blind/shutter position, the state refreshes right away instead of waiting for the next poll interval. (`cover.py`)

- **No crash for bulbs without color data** — If a FRITZ!DECT 500 returns `None` for hue or saturation, the integration no longer raises a `TypeError`. The official integration removed this guard and will crash in that case. (`light.py`)

- **Climate platform loads correctly** — A missing `callback` import that caused a `NameError` when loading the climate platform is fixed. (`climate.py`)

- **No stuck error state on malformed XML** — A garbled XML response from the FRITZ!Box during startup (e.g. during reboot) no longer leaves the integration in an error state requiring a manual reload. The integration now automatically retries instead. (`coordinator.py`)

### ✨ Improvements

- **Routines included in diagnostic exports** — FRITZ!SmartHome triggers (routines) are now part of the HA diagnostic download. (`diagnostics.py`)

- **Readable log messages** — The coordinator name in HA logs shows the FRITZ!Box hostname instead of the internal config entry ID. (`coordinator.py`)

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
