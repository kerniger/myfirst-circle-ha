# Sanitized protocol notes

This document records only the minimum technical behavior needed to maintain
the integration. It intentionally contains no account data, session values,
device identifiers, coordinates, captures, or local research paths.

## Service

The current production API base URL is:

```text
https://socialcircle.app
```

The integration uses these operations:

```text
GET  /api/country/
POST /api/user/login
POST /auth/api/v1/refreshuserauth
GET  /v2/api/user/child
GET  /v2/api/device/listdevice
GET  /v2/api/device/info
PUT  /v2/api/device/
```

## Authentication summary

The Android client contains an app-wide anonymous client seed used before a
user signs in. It is constant across clean installations and Android users and
contains no account, device, or installation data. A successful phone/password
login returns a renewable API credential and a parent user token. Only those
two resulting values are persisted in the Home Assistant config entry.

The login endpoint also expects app-like device metadata, a Circle-internal
country ID, and two non-empty 64-character device identifiers. The integration
resolves the country ID from the international phone prefix and derives stable
pseudonymous identifiers with SHA-256. It does not transmit the Home Assistant
host name, hardware ID, or a real phone identifier.

## Read sequence

1. Fetch children visible to the parent token.
2. Fetch watches for each child's token.
3. Fetch the current device information by watch identifier.
4. Parse location and status in memory.

## Active location request

The Android app's manual location button sends `PUT /v2/api/device/` with the
watch identifier, child token, `devicetype` set to `WATCH`, `langID` set to
`en`, and `refreshlocation` set to the current Unix time in milliseconds as a
string. The integration reproduces this request only when its per-watch Home
Assistant button is pressed. It waits 15 seconds before polling device info
again and enforces a 60-second per-watch cooldown to limit battery impact.

Home Assistant registry identifiers are SHA-256 hashes of the watch identifier.
The raw identifier, child token, names, and coordinates are excluded from
diagnostics and logs.

## Operational behavior

The cloud uses success codes `0`, `200`, and `1000`. HTTP 401/403 responses are
treated as authentication failures. The integration first tries to renew the
session, then raises Home Assistant's authentication failure so the UI can
start reauthentication when renewal is no longer possible.

Regular polling is passive. Active location requests happen only after an
explicit button press because repeated requests may increase watch battery use.
