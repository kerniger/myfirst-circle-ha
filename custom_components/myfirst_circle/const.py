"""Constants for the myFirst Circle integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "myfirst_circle"

CONF_AUTHORIZATION = "authorization"
CONF_USER_TOKEN = "user_token"
CONF_PHONE = "phone"
CONF_PASSWORD = "password"

# App-wide anonymous client credential used by myFirst Circle 4.1.1 before a
# user signs in. It contains no account, device, or installation data.
DEFAULT_CLIENT_AUTHORIZATION = "mfapp.77e5b249kd2_d0dc1254defffc5ea39e9ef4d2e5cd07b1e6e9a560faec700c8e1f877b1de6c01f49922529bcc46fae7d3bdea56a0389f34ff53e94b44b68798ab4f0ff54a6c056f5da24b4fb48f0181874"
CLIENT_PREFIX_LENGTH = 18

DEFAULT_BASE_URL = "https://socialcircle.app"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=3)
LOCATION_REFRESH_COOLDOWN = timedelta(seconds=60)
LOCATION_REFRESH_DELAY = timedelta(seconds=15)

PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
]
