# Changelog

All notable changes to this project are documented here.

## 0.4.0 — 2026-08-17

- Add a translated per-watch button for requesting a fresh location.
- Reproduce the Circle app's active-location request without requiring the app.
- Poll the cloud 15 seconds after a request to pick up the new watch position.
- Add a 60-second per-watch cooldown to limit accidental battery drain.

## 0.3.0 — 2026-08-17

- Add complete first-time phone/password login without an existing app session.
- Resolve Circle's internal country ID automatically.
- Generate pseudonymous app-compatible device identifiers.
- Persist only the renewable session, never the phone number or password.
- Add automatic session renewal and Home Assistant reauthentication.
- Add redacted diagnostics without personal, device, or location data.
- Add a GPS device tracker and diagnostic battery sensor for every visible watch.
- Add translations for ten languages and local brand assets.
- Add HACS metadata, validation workflows, documentation, and an MIT license.
