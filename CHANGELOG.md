# Changelog

## Unreleased - 2026-08-25

### Fixed

- Report a clear, actionable `ImportError` when `geopy` is unavailable during node geocoding instead of returning `None` and later raising an unrelated unpacking error.
