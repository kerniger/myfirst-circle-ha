"""Diagnostics support for myFirst Circle."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from . import CircleConfigEntry
from .const import CONF_AUTHORIZATION, CONF_USER_TOKEN

TO_REDACT = {CONF_AUTHORIZATION, CONF_USER_TOKEN}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CircleConfigEntry
) -> dict[str, Any]:
    """Return diagnostics without personal, device, or location data."""
    coordinator = entry.runtime_data.coordinator
    return {
        "config_entry": {
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "watch_count": len(coordinator.devices),
            "location_record_count": len(coordinator.data or {}),
        },
    }
