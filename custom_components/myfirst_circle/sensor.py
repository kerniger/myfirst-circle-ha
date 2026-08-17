"""Diagnostic sensors for myFirst Circle watches."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CircleConfigEntry
from .const import DOMAIN
from .coordinator import CircleCoordinator
from .models import CircleDevice, device_identifier


async def async_setup_entry(hass, entry: CircleConfigEntry, async_add_entities) -> None:
    """Set up diagnostic entities for every discovered watch."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        CircleBatterySensor(coordinator, device) for device in coordinator.devices
    )


class CircleBatterySensor(CoordinatorEntity[CircleCoordinator], SensorEntity):
    """Battery level reported by one myFirst watch."""

    _attr_has_entity_name = True
    _attr_translation_key = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: CircleCoordinator, device: CircleDevice) -> None:
        super().__init__(coordinator)
        self.device = device
        identifier = device_identifier(device.imei)
        self._attr_unique_id = f"{identifier}_battery"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)},
            name=device.child_name,
            manufacturer=device.manufacturer or "myFirst",
            model=device.model or device.device_type,
        )

    @property
    def native_value(self) -> int | None:
        info = self.coordinator.data.get(self.device.imei)
        return info.battery if info else None
