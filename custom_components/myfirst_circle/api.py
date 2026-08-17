"""Async client for the private myFirst Circle cloud API."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from aiohttp import ClientError, ClientResponse, ClientSession

from .const import CLIENT_PREFIX_LENGTH, DEFAULT_BASE_URL
from .models import (
    CircleChild,
    CircleDevice,
    CircleDeviceInfo,
    CirclePayloadError,
    CircleSession,
    build_location_refresh_payload,
    parse_children,
    parse_device_info,
    parse_devices,
    parse_session,
)


class CircleApiError(Exception):
    """Base error for Circle cloud communication."""


class CircleAuthenticationError(CircleApiError):
    """Raised when Circle rejects the configured credential."""


class CircleConnectionError(CircleApiError):
    """Raised when the Circle cloud cannot be reached."""


class CircleApiClient:
    """Small client for the endpoints used by the integration."""

    def __init__(
        self,
        session: ClientSession,
        authorization: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        on_session_update: Callable[[str, str], None] | None = None,
    ) -> None:
        self._session = session
        self._authorization = authorization
        if len(authorization) < CLIENT_PREFIX_LENGTH:
            raise CircleAuthenticationError("Invalid Circle client credential")
        self._client_prefix = authorization[:CLIENT_PREFIX_LENGTH]
        self._base_url = base_url.rstrip("/")
        self._on_session_update = on_session_update
        self._refresh_lock = asyncio.Lock()

    @property
    def authorization(self) -> str:
        """Return the current full Authorization credential."""
        return self._authorization

    async def _decode(self, response: ClientResponse) -> dict[str, Any]:
        if response.status in (401, 403):
            raise CircleAuthenticationError("Circle rejected the credential")
        if response.status >= 400:
            raise CircleApiError(f"Circle returned HTTP {response.status}")
        try:
            payload = await response.json(content_type=None)
        except (ValueError, TypeError) as err:
            raise CircleApiError("Circle returned invalid JSON") from err
        if not isinstance(payload, dict):
            raise CircleApiError("Circle returned an invalid response")
        code = payload.get("code")
        if isinstance(code, int) and code not in (0, 200, 1000):
            raise CircleApiError(f"Circle returned API code {code}")
        return payload

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        empty_body: bool = False,
        retry_auth: bool = True,
    ) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "Authorization": self._authorization,
            "Content-Type": "application/json",
            "User-Agent": "myFirst Circle Home Assistant/0.4",
        }
        try:
            async with self._session.request(
                method,
                f"{self._base_url}{path}",
                params=params,
                json=json_data,
                data=b"" if empty_body else None,
                headers=headers,
                timeout=20,
            ) as response:
                return await self._decode(response)
        except CircleAuthenticationError:
            if not retry_auth:
                raise
            await self.async_refresh_session()
            return await self._request(
                method,
                path,
                params=params,
                json_data=json_data,
                empty_body=empty_body,
                retry_auth=False,
            )
        except CircleApiError:
            raise
        except (ClientError, TimeoutError) as err:
            raise CircleConnectionError("Unable to reach Circle") from err

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    def _apply_session(self, session: CircleSession) -> None:
        """Replace the encrypted token while retaining the client prefix."""
        self._authorization = self._client_prefix + session.api_token
        if self._on_session_update is not None:
            self._on_session_update(self._authorization, session.user_token)

    async def async_refresh_session(self) -> CircleSession:
        """Refresh the API credential without using the Android app."""
        async with self._refresh_lock:
            payload = await self._request(
                "POST",
                "/auth/api/v1/refreshuserauth",
                empty_body=True,
                retry_auth=False,
            )
            try:
                session = parse_session(payload)
            except CirclePayloadError as err:
                raise CircleAuthenticationError(str(err)) from err
            self._apply_session(session)
            return session

    async def async_login(self, phone: str, password: str) -> CircleSession:
        """Create a user session using the phone/password account flow.

        The anonymous app-wide client credential is sufficient for a new
        installation. The successful session replaces it in memory.
        """
        normalized_phone = self._normalize_phone(phone)
        country_id = await self._async_country_id(normalized_phone)
        try:
            payload = await self._request(
                "POST",
                "/api/user/login",
                json_data={
                    "btmac": self._device_identifier(normalized_phone, "btmac"),
                    "devicemodel": "BTV-DL09",
                    "imei": self._device_identifier(normalized_phone, "imei"),
                    "langID": str(country_id),
                    "manufacture": "HUAWEI",
                    "os": "Android",
                    "osversion": "14",
                    "password": password,
                    "phone": normalized_phone,
                    "selectedtranslation": "en",
                    "token": "",
                },
                retry_auth=False,
            )
        except CircleConnectionError:
            raise
        except CircleApiError as err:
            raise CircleAuthenticationError("Circle rejected the login") from err
        try:
            session = parse_session(payload)
        except CirclePayloadError as err:
            raise CircleAuthenticationError(str(err)) from err
        self._apply_session(session)
        return session

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize an international phone number for the Circle API."""
        compact = "".join(character for character in phone if character.isdigit())
        if phone.strip().startswith("+"):
            return "+" + compact
        if compact.startswith("00"):
            return "+" + compact[2:]
        raise CircleAuthenticationError(
            "Phone number must include an international country code"
        )

    @staticmethod
    def _device_identifier(phone: str, purpose: str) -> str:
        """Create an app-compatible pseudonymous device identifier."""
        return hashlib.sha256(
            f"myfirst-circle-ha:{purpose}:{phone}".encode()
        ).hexdigest()

    async def _async_country_id(self, phone: str) -> int:
        """Resolve Circle's country ID from the longest phone-code match."""
        payload = await self._request("GET", "/api/country/", retry_auth=False)
        countries = payload.get("data")
        if not isinstance(countries, list):
            raise CircleAuthenticationError("Circle returned no country list")

        matches: list[tuple[int, int]] = []
        for country in countries:
            if not isinstance(country, dict):
                continue
            country_id = country.get("id")
            phone_code = country.get("phone_code")
            if not isinstance(country_id, int) or not isinstance(phone_code, str):
                continue
            normalized_code = "+" + "".join(
                character for character in phone_code if character.isdigit()
            )
            if phone.startswith(normalized_code):
                matches.append((len(normalized_code), country_id))
        if not matches:
            raise CircleAuthenticationError(
                "Circle does not recognize the country code"
            )
        return max(matches)[1]

    async def async_get_children(self, parent_token: str) -> list[CircleChild]:
        """Return child accounts associated with a parent token."""
        payload = await self._get(
            "/v2/api/user/child",
            {"pageNum": 1, "pageSize": 100, "userToken": parent_token},
        )
        try:
            return parse_children(payload)
        except CirclePayloadError as err:
            raise CircleApiError(str(err)) from err

    async def async_get_devices(self, child: CircleChild) -> list[CircleDevice]:
        """Return watches bound to a child account."""
        payload = await self._get(
            "/v2/api/device/listdevice", {"usertoken": child.token}
        )
        try:
            return parse_devices(
                payload, child_token=child.token, child_name=child.name
            )
        except CirclePayloadError as err:
            raise CircleApiError(str(err)) from err

    async def async_discover_devices(self, parent_token: str) -> list[CircleDevice]:
        """Discover all watches visible through the configured parent account."""
        children = await self.async_get_children(parent_token)
        devices: list[CircleDevice] = []
        for child in children:
            devices.extend(await self.async_get_devices(child))
        return devices

    async def async_get_device_info(self, imei: str) -> CircleDeviceInfo:
        """Return current coordinates and status for one watch."""
        payload = await self._get("/v2/api/device/info", {"imei": imei})
        try:
            return parse_device_info(payload, retrieved_at=datetime.now(UTC))
        except CirclePayloadError as err:
            raise CircleApiError(str(err)) from err

    async def async_request_location(self, device: CircleDevice) -> None:
        """Ask a watch for a fresh location using the Android app protocol."""
        await self._request(
            "PUT",
            "/v2/api/device/",
            json_data=build_location_refresh_payload(
                device, time.time_ns() // 1_000_000
            ),
        )
