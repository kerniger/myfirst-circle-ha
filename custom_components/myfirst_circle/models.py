"""Response models and parsers for the myFirst Circle API."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class CirclePayloadError(ValueError):
    """Raised when a Circle response does not have the expected structure."""


def device_identifier(imei: str) -> str:
    """Return a stable identifier without persisting the watch IMEI."""
    return hashlib.sha256(imei.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CircleChild:
    """A child account visible to the parent account."""

    token: str
    name: str


@dataclass(frozen=True, slots=True)
class CircleDevice:
    """A watch returned by listdevice."""

    imei: str
    user_token: str
    child_name: str
    model: str | None = None
    device_type: str | None = None
    manufacturer: str | None = None
    operating_system: str | None = None
    os_version: str | None = None


@dataclass(frozen=True, slots=True)
class CircleDeviceInfo:
    """Current data returned by device/info."""

    imei: str
    latitude: float | None
    longitude: float | None
    battery: int | None
    label: str | None
    model: str | None
    smart_location_enabled: bool | None
    is_charging: bool | None
    is_low_battery: bool | None
    is_turned_on: bool | None
    retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class CircleSession:
    """Tokens returned by login or refreshuserauth."""

    api_token: str
    user_token: str


def build_location_refresh_payload(
    device: CircleDevice, requested_at_ms: int
) -> dict[str, str]:
    """Build the active-location payload used by the Circle Android app."""
    return {
        "devicetype": "WATCH",
        "imei": device.imei,
        "langID": "en",
        "refreshlocation": str(requested_at_ms),
        "token": device.user_token,
    }


def _response_data(payload: Any) -> Any:
    if not isinstance(payload, dict):
        raise CirclePayloadError("Circle response is not an object")
    if "data" not in payload:
        raise CirclePayloadError("Circle response has no data field")
    return payload["data"]


def _first_string(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def parse_children(payload: Any) -> list[CircleChild]:
    """Parse /v2/api/user/child."""
    data = _response_data(payload)
    if isinstance(data, dict):
        items = data.get("listItem", data.get("ListItem", []))
    else:
        items = data
    if not isinstance(items, list):
        raise CirclePayloadError("Circle child list is not an array")

    children: list[CircleChild] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        token = _first_string(item, "token", "Token", "userToken", "UserToken")
        if not token:
            continue
        name = _first_string(item, "name", "Name", "fullname", "Fullname")
        children.append(CircleChild(token=token, name=name or "myFirst watch"))
    return children


def parse_devices(
    payload: Any, *, child_token: str, child_name: str
) -> list[CircleDevice]:
    """Parse /v2/api/device/listdevice."""
    data = _response_data(payload)
    if not isinstance(data, dict):
        raise CirclePayloadError("Circle device response is not an object")
    items = data.get("Devices", data.get("devices", []))
    if not isinstance(items, list):
        raise CirclePayloadError("Circle device list is not an array")

    devices: list[CircleDevice] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        imei = _first_string(item, "IMEI", "imei")
        if not imei:
            continue
        devices.append(
            CircleDevice(
                imei=imei,
                user_token=child_token,
                child_name=child_name,
                model=_first_string(item, "DeviceModel", "devicemodel"),
                device_type=_first_string(item, "DeviceType", "devicetype"),
                manufacturer=_first_string(item, "Manufacture", "manufacture"),
                operating_system=_first_string(item, "OS", "os"),
                os_version=_first_string(item, "OSVersion", "osversion"),
            )
        )
    return devices


def parse_device_info(payload: Any, *, retrieved_at: datetime) -> CircleDeviceInfo:
    """Parse /v2/api/device/info."""
    data = _response_data(payload)
    if not isinstance(data, dict):
        raise CirclePayloadError("Circle device info is not an object")
    imei = _first_string(data, "imei", "IMEI")
    if not imei:
        raise CirclePayloadError("Circle device info has no IMEI")

    status = data.get("devicestatus")
    if not isinstance(status, dict):
        status = {}
    return CircleDeviceInfo(
        imei=imei,
        latitude=_optional_float(data.get("latitude")),
        longitude=_optional_float(data.get("longitude")),
        battery=_optional_int(data.get("battery")),
        label=_first_string(data, "devicelabel", "DeviceLabel"),
        model=_first_string(data, "devicemodel", "DeviceModel"),
        smart_location_enabled=_optional_bool(data.get("enablesmartloc")),
        is_charging=_optional_bool(status.get("ischarging")),
        is_low_battery=_optional_bool(status.get("islowbatt")),
        is_turned_on=_optional_bool(status.get("isturnedon")),
        retrieved_at=retrieved_at,
    )


def parse_session(payload: Any) -> CircleSession:
    """Parse the common login/refresh token response."""
    data = _response_data(payload)
    if not isinstance(data, dict):
        raise CirclePayloadError("Circle session response is not an object")

    api_token = _first_string(data, "authtoken", "authToken", "apiToken")
    user_token = _first_string(data, "token", "userToken", "usertoken")
    profile = data.get("data")
    if not user_token and isinstance(profile, dict):
        user_token = _first_string(profile, "token", "userToken", "usertoken")
    if not api_token or not user_token:
        raise CirclePayloadError("Circle session response has no tokens")
    return CircleSession(api_token=api_token, user_token=user_token)
