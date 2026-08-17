"""Config flow for myFirst Circle."""

from __future__ import annotations

import hashlib
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    CircleApiClient,
    CircleApiError,
    CircleAuthenticationError,
    CircleConnectionError,
)
from .const import (
    CONF_AUTHORIZATION,
    CONF_PASSWORD,
    CONF_PHONE,
    CONF_USER_TOKEN,
    DEFAULT_CLIENT_AUTHORIZATION,
    DOMAIN,
)


class NoDevicesFound(CircleApiError):
    """Raised when the account has no watches."""


async def _validate_input(hass, phone: str, password: str) -> tuple[int, str, str]:
    api = CircleApiClient(async_get_clientsession(hass), DEFAULT_CLIENT_AUTHORIZATION)
    session = await api.async_login(phone, password)
    devices = await api.async_discover_devices(session.user_token)
    if not devices:
        raise NoDevicesFound("No watches found")
    return len(devices), api.authorization, session.user_token


class CircleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a myFirst Circle config flow."""

    VERSION = 1

    @staticmethod
    def _credentials_schema() -> vol.Schema:
        """Return the shared login schema."""
        password = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
        return vol.Schema(
            {
                vol.Required(CONF_PHONE): str,
                vol.Required(CONF_PASSWORD): password,
            }
        )

    async def _async_validate_credentials(
        self, user_input: dict[str, Any]
    ) -> tuple[int, str, str] | dict[str, str]:
        """Validate credentials and map failures to config-flow errors."""
        phone = str(user_input[CONF_PHONE]).strip()
        password_value = str(user_input[CONF_PASSWORD])
        try:
            return await _validate_input(self.hass, phone, password_value)
        except CircleAuthenticationError:
            return {"base": "invalid_auth"}
        except CircleConnectionError:
            return {"base": "cannot_connect"}
        except NoDevicesFound:
            return {"base": "no_devices"}
        except CircleApiError:
            return {"base": "unknown"}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up Circle credentials entered by the user."""
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_validate_credentials(user_input)
            if isinstance(result, tuple):
                count, authorization, user_token = result
                unique_id = hashlib.sha256(user_token.encode()).hexdigest()
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"myFirst Circle ({count})",
                    data={
                        CONF_AUTHORIZATION: authorization,
                        CONF_USER_TOKEN: user_token,
                    },
                )
            errors = result

        return self.async_show_form(
            step_id="user",
            data_schema=self._credentials_schema(),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start reauthentication for an expired Circle session."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace an expired session after a fresh direct login."""
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_validate_credentials(user_input)
            if isinstance(result, tuple):
                _, authorization, user_token = result
                entry = self._get_reauth_entry()
                unique_id = hashlib.sha256(user_token.encode()).hexdigest()
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_AUTHORIZATION: authorization,
                        CONF_USER_TOKEN: user_token,
                    },
                )
            else:
                errors = result

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=self._credentials_schema(),
            errors=errors,
        )
