"""GPS device trackers for myFirst Circle watches."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CircleConfigEntry
from .const import DOMAIN
from .coordinator import CircleCoordinator
from .models import CircleDevice, device_identifier


async def async_setup_entry(hass, entry: CircleConfigEntry, async_add_entities) -> None:
    """Set up a tracker for every discovered watch."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CircleTracker(coordinator, device) for device in coordinator.devices
    )


class CircleTracker(CoordinatorEntity[CircleCoordinator], TrackerEntity):
    """Current location of one myFirst watch."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: CircleCoordinator, device: CircleDevice) -> None:
        super().__init__(coordinator)
        self.device = device
        identifier = device_identifier(device.imei)
        self._attr_unique_id = f"{identifier}_location"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            name=device.child_name,
            manufacturer=device.manufacturer or "myFirst",
            model=device.model or device.device_type,
        )

    @property
    def latitude(self) -> float | None:
        info = self.coordinator.data.get(self.device.imei)
        return info.latitude if info else None

    @property
    def longitude(self) -> float | None:
        info = self.coordinator.data.get(self.device.imei)
        return info.longitude if info else None

    @property
    def location_accuracy(self) -> float:
        return 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        info = self.coordinator.data.get(self.device.imei)
        if info is None:
            return {}
        return {
            "retrieved_at": info.retrieved_at.isoformat(),
            "smart_location_enabled": info.smart_location_enabled,
            "is_charging": info.is_charging,
            "is_low_battery": info.is_low_battery,
            "is_turned_on": info.is_turned_on,
        }
