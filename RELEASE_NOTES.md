# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

- `LatestValueCache` now takes an optional `key` function, which returns the key for each incoming message, and the latest value for each key is cached and can be retrieved separately.  

## Bug Fixes

- Fix `NopReceiver.ready()` to properly terminate when receiver is closed.
