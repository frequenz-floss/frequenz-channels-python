# Frequenz Channels Release Notes

## Summary

This is a bugfix release that mainly uses more up to date dependencies and extend the range of supported dependencies.  There is technically one breaking change though, but this is hardly used by anyone.

## Upgrading

* `FileWatcher` no longer accepts or sets `None` as the `event_types` argument. Instead, all available event types are now set by default while still providing the flexibility to customize the event types as needed.

## Bug Fixes

* Many documentation examples were fixed.
