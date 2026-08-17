# myFirst Circle for Home Assistant

An unofficial Home Assistant integration that exposes the latest location and
battery level of watches linked to a myFirst Circle account.

## Features

- Direct sign-in with an international phone number and password
- No Android app, tablet, copied token, or manual API setup required
- One GPS `device_tracker` per linked watch
- One diagnostic battery sensor per linked watch
- Automatic session renewal and a UI reauthentication flow
- Three-minute passive cloud polling without requesting a new GPS fix
- Stable hashed Home Assistant identifiers instead of watch IMEIs
- English, German, French, Spanish, Italian, Dutch, Portuguese, Polish,
  Japanese, and Simplified Chinese UI text

## Installation

### HACS

1. Open HACS in Home Assistant.
2. Add `https://github.com/kerniger/myfirst-circle-ha` as a custom
   **Integration** repository.
3. Install **myFirst Circle**.
4. Restart Home Assistant.

### Manual

Copy `custom_components/myfirst_circle` into the `custom_components` directory
of your Home Assistant configuration, then restart Home Assistant.

## Configuration

Go to **Settings → Devices & services → Add integration**, search for
**myFirst Circle**, and enter:

- the Circle account phone number in international format, such as
  `+12025550123`; and
- the Circle account password.

The phone number and password are used only for the login request and are not
stored. Home Assistant stores the renewable cloud session returned by Circle.
If that session can no longer be renewed, Home Assistant asks for the same
account credentials again.

Circle appears to handle simultaneous sessions inconsistently. A separate
adult Circle account with access to the same family/watch is recommended for
Home Assistant, so signing into the phone app does not interfere with the
automation account.

## Entities and polling

For each visible watch, the integration creates:

- a GPS `device_tracker` with the latest coordinates returned by the Circle
  cloud; and
- a diagnostic battery sensor.

The integration reads the already available cloud location every three
minutes. It does not actively ask the watch for a fresh GPS position, avoiding
additional watch battery use. Consequently, the location timestamp may be
older than the Home Assistant poll time.

## Privacy and security

- Phone number and password are never persisted by this integration.
- Session credentials are stored in the Home Assistant config entry, like
  credentials for other cloud integrations.
- Watch IMEIs are held only in memory while the integration is running; the
  device and entity registries receive SHA-256 identifiers instead.
- Downloaded diagnostics redact all session credentials and contain no names,
  IMEIs, coordinates, or location details.
- Debug logs intentionally do not include request headers, query values, or
  response bodies.

Please remove personal data and credentials from logs before attaching them to
a public issue.

## Compatibility and limitations

- Tested with Home Assistant 2026.8 and myFirst Circle app/API behavior from
  Circle 4.1.1.
- This integration relies on an undocumented private cloud API. The vendor can
  change or disable it without notice.
- Phone/password login is supported. Social sign-in methods are not supported.
- The integration is read-only and does not expose history, safe-zone editing,
  tracking mode, or an active location refresh.
- A watch must already be linked and visible to the account used during setup.

## Support and development

Open a [GitHub issue](https://github.com/kerniger/myfirst-circle-ha/issues) for
bugs or feature requests. Development and test instructions are in
[CONTRIBUTING.md](CONTRIBUTING.md). A sanitized protocol overview is available
in [docs/PROTOCOL.md](docs/PROTOCOL.md).

## Disclaimer

This is an independent community project and is not affiliated with, endorsed
by, or supported by myFirst or Oaxis. Product and company names are trademarks
of their respective owners. The bundled icon is an original generic
watch/location symbol and is not an official myFirst logo.

## License

MIT — see [LICENSE](LICENSE).
