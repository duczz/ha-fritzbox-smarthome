"""Support for AVM FRITZ!SmartHome cover devices."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .coordinator import FritzboxConfigEntry
from .entity import FritzBoxDeviceEntity, async_setup_fritz_device_entities

# Coordinator handles data updates, so we can allow unlimited parallel updates
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FritzboxConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the FRITZ!SmartHome cover from ConfigEntry."""
    coordinator = entry.runtime_data
    async_setup_fritz_device_entities(
        coordinator,
        entry,
        async_add_entities,
        lambda ain: (
            [FritzboxCover(coordinator, ain)]
            if coordinator.data.devices[ain].has_blind
            else []
        ),
    )


class FritzboxCover(FritzBoxDeviceEntity, CoverEntity):
    """The cover class for FRITZ!SmartHome covers."""

    _attr_device_class = CoverDeviceClass.BLIND
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.SET_POSITION
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
    )

    @property
    def current_cover_position(self) -> int | None:
        """Return the current position."""
        position = None
        if self.data.levelpercentage is not None:
            position = 100 - self.data.levelpercentage
        return position

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed."""
        if self.data.levelpercentage is None:
            return None
        return self.data.levelpercentage == 100  # type: ignore [no-any-return]

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        try:
            await self.hass.async_add_executor_job(self.data.set_blind_open, True)
        except Exception as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cover_operation_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.coordinator.async_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        try:
            await self.hass.async_add_executor_job(self.data.set_blind_close, True)
        except Exception as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cover_operation_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.coordinator.async_refresh()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        try:
            await self.hass.async_add_executor_job(
                self.data.set_level_percentage, 100 - kwargs[ATTR_POSITION], True
            )
        except Exception as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cover_operation_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.coordinator.async_refresh()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        try:
            await self.hass.async_add_executor_job(self.data.set_blind_stop, True)
        except Exception as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="cover_operation_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        await self.coordinator.async_refresh()
