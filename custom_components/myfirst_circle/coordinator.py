"""Data coordinator for myFirst Circle."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    CircleApiClient,
    CircleApiError,
    CircleAuthenticationError,
    CircleConnectionError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .models import CircleDevice, CircleDeviceInfo

_LOGGER = logging.getLogger(__name__)


class CircleCoordinator(DataUpdateCoordinator[dict[str, CircleDeviceInfo]]):
    """Coordinate polling of all watches in one Circle account."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: CircleApiClient,
        parent_token: str,
    ) -> None:
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api
        self.parent_token = parent_token
        self.devices: list[CircleDevice] = []

    async def async_initialize(self) -> None:
        """Discover watches and perform the first location update."""
        try:
            self.devices = await self.api.async_discover_devices(self.parent_token)
        except CircleAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except CircleConnectionError as err:
            raise ConfigEntryNotReady from err
        except CircleApiError as err:
            raise ConfigEntryNotReady from err
        await self.async_config_entry_first_refresh()

    async def _async_update_data(self) -> dict[str, CircleDeviceInfo]:
        try:
            info = await asyncio.gather(
                *(
                    self.api.async_get_device_info(device.imei)
                    for device in self.devices
                )
            )
        except CircleAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except CircleApiError as err:
            raise UpdateFailed(str(err)) from err
        return {item.imei: item for item in info}
