"""Active location refresh buttons for myFirst Circle watches."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CircleConfigEntry
from .api import CircleApiError
from .const import DOMAIN
from .coordinator import CircleCoordinator, CircleLocationRefreshCooldown
from .models import CircleDevice, device_identifier


async def async_setup_entry(hass, entry: CircleConfigEntry, async_add_entities) -> None:
    """Set up an active-location button for every discovered watch."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CircleLocationRefreshButton(coordinator, device)
        for device in coordinator.devices
    )


class CircleLocationRefreshButton(CoordinatorEntity[CircleCoordinator], ButtonEntity):
    """Request a fresh position from one myFirst watch."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh_location"
    _attr_icon = "mdi:crosshairs-gps"

    def __init__(self, coordinator: CircleCoordinator, device: CircleDevice) -> None:
        super().__init__(coordinator)
        self.device = device
        identifier = device_identifier(device.imei)
        self._attr_unique_id = f"{identifier}_refresh_location"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            name=device.child_name,
            manufacturer=device.manufacturer or "myFirst",
            model=device.model or device.device_type,
        )

    async def async_press(self) -> None:
        """Ask the watch to report a fresh location."""
        try:
            await self.coordinator.async_request_location(self.device)
        except CircleLocationRefreshCooldown as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="refresh_cooldown",
                translation_placeholders={
                    "seconds": str(err.remaining_seconds),
                },
            ) from err
        except CircleApiError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="refresh_failed",
            ) from err
