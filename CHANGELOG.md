# Changelog – FritzBox Home Assistant Integration

## [Unreleased]

### Bugfixes

#### `coordinator.py` — Leere Fehlermeldung in `UpdateFailed`
- **Problem:** `UpdateFailed` wurde ohne Argument raised (`raise UpdateFailed from ex`). Im Home Assistant Log erschien damit nur eine leere Meldung:
  ```
  Error fetching d6db4e72b949d4f3ce820d47da1ac880 data:
  ```
  Die eigentliche Fehlerursache war nicht ersichtlich.
- **Fix:** `UpdateFailed(ex)` — die Original-Exception wird als Argument übergeben und im Log ausgegeben.

#### `coordinator.py` — Kompletter Integration-Reload bei temporären Verbindungsfehlern
- **Problem:** Bei jedem `RequestConnectionError`, `HTTPError` oder `LoginError` wurde `async_schedule_reload` aufgerufen. Die gesamte Integration wurde neu geladen, alle Entities kurz entfernt und wieder angelegt. Das war besonders problematisch bei nächtlichen DSL-Zwangstrennungen: Die FritzBox ist lokal weiterhin erreichbar, aber die Session (SID) ist abgelaufen — ein Re-Login hätte gereicht.
  Außerdem wurde `LoginError` im `_async_update_data`-Pfad bisher gar nicht abgefangen.
- **Fix:** Re-Login + Retry-Pattern in `_async_update_data` eingeführt:
  1. Erster Fehler (`RequestConnectionError` / `HTTPError` / `LoginError`) → Re-Login via `fritz.login()`
  2. Re-Login schlägt mit `LoginError` fehl → `ConfigEntryAuthFailed` (Credentials ungültig)
  3. Re-Login schlägt mit Verbindungsfehler fehl → `UpdateFailed(conn_ex)`
  4. Retry des Datenabrufs schlägt erneut fehl → `UpdateFailed(retry_ex)`
  5. Kein `async_schedule_reload` mehr.

  ```python
  except (RequestConnectionError, HTTPError, LoginError) as ex:
      try:
          await self.hass.async_add_executor_job(self.fritz.login)
      except LoginError as login_ex:
          raise ConfigEntryAuthFailed from login_ex
      except (RequestConnectionError, HTTPError) as conn_ex:
          raise UpdateFailed(conn_ex) from conn_ex
      try:
          new_data = await self.hass.async_add_executor_job(self._update_fritz_devices)
      except (RequestConnectionError, HTTPError, LoginError) as retry_ex:
          raise UpdateFailed(retry_ex) from retry_ex
  ```

#### `cover.py` — Fehlender `async_refresh()` nach `set_position`
- **Problem:** `async_set_cover_position` rief nach dem API-Call kein `coordinator.async_refresh()` auf. Der HA-Status wurde nach einer Positionsänderung nicht aktualisiert, während `open`, `close` und `stop` das korrekt taten.
- **Fix:** `await self.coordinator.async_refresh()` am Ende von `async_set_cover_position` ergänzt.

#### `light.py` — `hs_color` konnte bei `None`-Werten crashen
- **Problem:** Die Property `hs_color` berechnete `float(saturation) * 100.0 / 255.0` ohne vorher zu prüfen, ob `hue` oder `saturation` vom Gerät als `None` zurückgegeben werden. Das führte zu einem `TypeError` bei Geräten, die keine Farbdaten liefern.
- **Fix:** Null-Guard eingefügt; die Property gibt nun `None` zurück wenn `hue is None or saturation is None`. Return-Typ von `tuple[float, float]` auf `tuple[float, float] | None` korrigiert.

#### `climate.py` — Fehlender `callback`-Import
- **Problem:** `@callback` wurde auf `async_write_ha_state` verwendet, aber `callback` fehlte im Import (`from homeassistant.core import HomeAssistant` — kein `callback`). Das führte zu einem `NameError` beim Laden der Plattform.
- **Fix:** `callback` zum Import ergänzt: `from homeassistant.core import HomeAssistant, callback`.

#### `coordinator.py` — Trigger-Entities wurden fälschlich aus der Entity Registry gelöscht
- **Problem:** `cleanup_removed_devices` baute `available_ains` nur aus `data.devices` und `data.templates`. `FritzboxTrigger`-Entities nutzen ihre AIN als `unique_id` — da Trigger-AIns nicht in `available_ains` enthalten waren, wurden alle Trigger-Entities bei jedem Cleanup-Durchlauf aus der Entity Registry gelöscht.
- **Fix:** `list(data.triggers)` zu `available_ains` ergänzt.

---

### Verbesserungen

#### `light.py` — Error Handling in `async_turn_on` / `async_turn_off`
- **Problem:** Alle API-Aufrufe (`set_level`, `set_unmapped_color`, `set_color`, `set_color_temp`, `set_state_on`, `set_state_off`) liefen ohne try/except. Bei einem Netzwerkfehler oder einer API-Exception propagierte der Fehler unkontrolliert, ohne dem Nutzer eine verständliche Fehlermeldung zu zeigen. Das Gerät konnte in einem inkonsistenten Zustand verbleiben.
- **Fix:** Alle API-Calls in `async_turn_on` in einen gemeinsamen `try/except`-Block gewickelt. `async_turn_off` ebenfalls abgesichert. Exceptions werden als `HomeAssistantError` mit dem Translation Key `light_operation_failed` re-raised. `coordinator.async_refresh()` findet weiterhin nur statt, wenn der API-Call erfolgreich war.
- **Neue Imports:** `HomeAssistantError` aus `homeassistant.exceptions`, `DOMAIN` aus `.const`.

#### `cover.py` — Error Handling in allen Cover-Operationen
- **Problem:** `async_open_cover`, `async_close_cover`, `async_set_cover_position` und `async_stop_cover` fingen keine Exceptions ab. Fehler vom FritzBox-API wurden still verschluckt oder unkontrolliert weitergegeben.
- **Fix:** Jede Methode wurde mit einem `try/except`-Block abgesichert. Exceptions werden als `HomeAssistantError` mit dem Translation Key `cover_operation_failed` re-raised.
- **Neue Imports:** `HomeAssistantError` aus `homeassistant.exceptions`, `DOMAIN` aus `.const`.

#### `button.py` — Error Handling in `async_press`
- **Problem:** Der `apply_template`-Aufruf in `async_press` hatte kein Error Handling. Schlägt das Anwenden eines Templates auf der FritzBox fehl (z. B. wegen Verbindungsproblem), bekam der Nutzer keine Rückmeldung.
- **Fix:** `try/except`-Block um `async_add_executor_job(self.apply_template)` ergänzt. Exception wird als `HomeAssistantError` mit dem Translation Key `template_failed` re-raised.
- **Neue Imports:** `HomeAssistantError` aus `homeassistant.exceptions`.

#### `switch.py` — Error Handling + Logging für Trigger-Operationen
- **Problem:** `FritzboxTrigger.async_turn_on` und `async_turn_off` fingen keine Exceptions ab. Fehler beim Aktivieren/Deaktivieren einer Routine wurden weder geloggt noch dem Nutzer gemeldet.
- **Fix:** Beide Methoden mit `try/except` abgesichert. Bei Fehler wird zuerst `LOGGER.error` mit AIN und Fehlerdetail geloggt, dann eine `HomeAssistantError` mit dem Translation Key `trigger_operation_failed` geworfen.
- **Neue Imports:** `LOGGER` aus `.const`.

#### `strings.json` — Neue Exception-Übersetzungen
- **Problem:** Für die neuen `HomeAssistantError`-Instanzen fehlten die zugehörigen Translation Keys im `exceptions`-Block.
- **Fix:** Sechs neue Einträge hinzugefügt:

  | Key | Message |
  |-----|---------|
  | `light_operation_failed` | `"Failed to change light setting: {error}"` |
  | `cover_operation_failed` | `"Failed to change cover: {error}"` |
  | `template_failed` | `"Failed to apply template: {error}"` |
  | `trigger_operation_failed` | `"Failed to change trigger state: {error}"` |
  | `switch_operation_failed` | `"Failed to change switch state: {error}"` |
  | `climate_operation_failed` | `"Failed to change thermostat setting: {error}"` |

#### `entity.py` — Gemeinsamer Helper `async_setup_fritz_device_entities`
- **Problem:** Das Setup-Boilerplate (Coordinator-Listener registrieren, initiale Entities adden, `new_devices` vs. alle Devices unterscheiden) war identisch in 5 Platform-Dateien wiederholt: `binary_sensor.py`, `climate.py`, `cover.py`, `light.py`, `sensor.py`.
- **Fix:** Helper-Funktion `async_setup_fritz_device_entities` in `entity.py` eingeführt. Nimmt eine `entity_factory: Callable[[str], Iterable[Entity]]` entgegen und kapselt das gesamte Listener/Setup-Pattern. Alle 5 Plattformen wurden umgestellt; `_add_entities` + `coordinator.async_add_listener` entfallen dort vollständig.
- **Neue Imports in `entity.py`:** `Callable`, `Iterable` aus `collections.abc`; `callback` aus `homeassistant.core`; `Entity` aus `homeassistant.helpers.entity`; `AddConfigEntryEntitiesCallback` aus `homeassistant.helpers.entity_platform`; `FritzboxConfigEntry` aus `.coordinator`.
- **Nicht umgestellt:** `switch.py` (verwaltet zusätzlich Triggers mit separatem Listener) und `button.py` (verwaltet Templates statt Devices) — beide bleiben unverändert.

#### `diagnostics.py` — Triggers in Diagnosedaten ergänzt + `vars()` abgesichert
- **Problem 1:** `coordinator.data.triggers` fehlte im Diagnose-Output. Aktive Routinen wurden bei einem Diagnose-Export komplett verschwiegen.
- **Fix 1:** `**coordinator.data.triggers` in das `entities`-Dict aufgenommen.
- **Problem 2:** `vars(entity)` liefert alle public Attribute des pyfritzhome-Objekts. `FritzhomeDevice` hat ein public `fritz`-Attribut das auf das Parent-`Fritzhome`-Objekt zeigt — dieses enthält Credentials (Username/Passwort). Der bisherige Filter `not k.startswith("_")` hätte es nicht herausgefiltert.
- **Fix 2:** Zusätzlicher `isinstance`-Filter — nur Basistypen (`str`, `int`, `float`, `bool`, `list`, `dict`, `None`) werden übernommen. Objekt-Referenzen wie `fritz` fallen damit automatisch raus, ohne Kenntnis interner Attributnamen.

#### `__init__.py` — Trigger-Devices bei Geräteentfernung berücksichtigt
- **Problem:** `async_remove_config_entry_device` prüfte ob ein Gerät zu `devices` oder `templates` gehört, um ein versehentliches Entfernen zu verhindern. Triggers wurden nicht geprüft — Trigger-Devices konnten daher fälschlich aus der Device Registry gelöscht werden.
- **Fix:** `or identifier[1] in coordinator.data.triggers` zur Prüfung ergänzt.

#### `sensor.py` — `suitable_*`-Funktionen durch Factory konsolidiert
- **Problem:** Vier Funktionen (`suitable_eco_temperature`, `suitable_comfort_temperature`, `suitable_nextchange_temperature`, `suitable_nextchange_time`) hatten alle identisch die Form `device.has_thermostat and device.ATTR is not None` und unterschieden sich nur im Attributnamen.
- **Fix:** Private Factory-Funktion `_suitable_thermostat_attr(attr)` eingeführt, die eine parametrisierte Check-Funktion zurückgibt. Die vier `suitable_*`-Namen bleiben als öffentliche Variablen erhalten (rückwärtskompatibel).

#### `switch.py` — `FritzboxSwitch` ohne Error Handling
- **Problem:** `async_turn_on` und `async_turn_off` des Schalters (nicht des Triggers) riefen `set_switch_state_on/off` ohne try/except auf. `FritzboxTrigger` in derselben Datei hatte das Error Handling bereits — inkonsistent.
- **Fix:** Beide Methoden mit `try/except` abgesichert. Exception wird als `HomeAssistantError` mit dem Translation Key `switch_operation_failed` re-raised.

#### `climate.py` — API-Calls ohne Error Handling
- **Problem:** `async_set_hkr_state` (`set_hkr_state`) und `async_set_temperature` (`set_target_temperature`) liefen ohne try/except. Netzwerkfehler oder API-Fehler propagierten unkontrolliert.
- **Fix:** Beide Methoden mit `try/except` abgesichert. Exceptions werden als `HomeAssistantError` mit dem Translation Key `climate_operation_failed` re-raised. `coordinator.async_refresh()` findet weiterhin nur statt, wenn der API-Call erfolgreich war.

---

### Nicht geändert (bekannte offene Punkte)

- **Coordinator-Refresh-Strategie:** Jede Operation löst weiterhin einen vollständigen `async_refresh()` aus. Eine gezieltere Zustandsaktualisierung (optimistic update) wurde nicht implementiert.
- **`state_class` für Power/Voltage/Current-Sensoren:** Alle drei haben bereits `SensorStateClass.MEASUREMENT` in `sensor.py` — kein Handlungsbedarf.
- **Lock-Behandlung via `HomeAssistantError`:** `switch.py` und `climate.py` werfen Exceptions statt `available = False` zu setzen. Dieser HA-Best-Practice-Verstoß wurde bewusst nicht geändert, da er das bestehende Verhalten grundlegend umstellen würde.
