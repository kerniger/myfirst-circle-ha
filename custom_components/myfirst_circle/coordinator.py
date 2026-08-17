"""Data coordinator for myFirst Circle."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections.abc import Callable
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    CircleApiClient,
    CircleApiError,
    CircleAuthenticationError,
    CircleConnectionError,
)
from .const import (
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOCATION_REFRESH_COOLDOWN,
    LOCATION_REFRESH_DELAY,
)
from .models import CircleDevice, CircleDeviceInfo

_LOGGER = logging.getLogger(__name__)


class CircleLocationRefreshCooldown(Exception):
    """Raised when an active location was requested too recently."""

    def __init__(self, remaining_seconds: int) -> None:
        super().__init__(remaining_seconds)
        self.remaining_seconds = remaining_seconds


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
        self._location_refresh_locks: dict[str, asyncio.Lock] = {}
        self._last_location_refresh: dict[str, float] = {}
        self._delayed_refresh_cancellations: set[Callable[[], None]] = set()

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

    async def async_request_location(self, device: CircleDevice) -> None:
        """Request a fresh watch fix and schedule a cloud-state follow-up."""
        lock = self._location_refresh_locks.setdefault(device.imei, asyncio.Lock())
        async with lock:
            last_refresh = self._last_location_refresh.get(device.imei)
            now = time.monotonic()
            if last_refresh is not None:
                remaining = LOCATION_REFRESH_COOLDOWN.total_seconds() - (
                    now - last_refresh
                )
                if remaining > 0:
                    raise CircleLocationRefreshCooldown(math.ceil(remaining))

            await self.api.async_request_location(device)
            self._last_location_refresh[device.imei] = time.monotonic()
            self._schedule_location_follow_up()

    def _schedule_location_follow_up(self) -> None:
        """Poll once after the watch has had time to report its new fix."""
        cancellation: Callable[[], None] | None = None

        async def async_follow_up(_now: datetime) -> None:
            if cancellation is not None:
                self._delayed_refresh_cancellations.discard(cancellation)
            await self.async_request_refresh()

        cancellation = async_call_later(
            self.hass, LOCATION_REFRESH_DELAY, async_follow_up
        )
        self._delayed_refresh_cancellations.add(cancellation)

    async def async_shutdown(self) -> None:
        """Cancel active-location follow-ups and shut down the coordinator."""
        for cancellation in self._delayed_refresh_cancellations:
            cancellation()
        self._delayed_refresh_cancellations.clear()
        await super().async_shutdown()
