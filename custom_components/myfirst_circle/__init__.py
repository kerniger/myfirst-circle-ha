"""myFirst Circle integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    CircleApiClient,
    CircleAuthenticationError,
    CircleConnectionError,
)
from .const import CONF_AUTHORIZATION, CONF_USER_TOKEN, PLATFORMS
from .coordinator import CircleCoordinator


@dataclass(slots=True)
class CircleRuntimeData:
    """Runtime data for one config entry."""

    coordinator: CircleCoordinator


type CircleConfigEntry = ConfigEntry[CircleRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: CircleConfigEntry) -> bool:
    """Set up myFirst Circle from a config entry."""

    def update_session(authorization: str, user_token: str) -> None:
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                CONF_AUTHORIZATION: authorization,
                CONF_USER_TOKEN: user_token,
            },
        )

    api = CircleApiClient(
        async_get_clientsession(hass),
        entry.data[CONF_AUTHORIZATION],
        on_session_update=update_session,
    )
    try:
        session = await api.async_refresh_session()
    except CircleAuthenticationError as err:
        raise ConfigEntryAuthFailed from err
    except CircleConnectionError as err:
        raise ConfigEntryNotReady from err
    coordinator = CircleCoordinator(hass, entry, api, session.user_token)
    await coordinator.async_initialize()
    entry.runtime_data = CircleRuntimeData(coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CircleConfigEntry) -> bool:
    """Unload a myFirst Circle config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
