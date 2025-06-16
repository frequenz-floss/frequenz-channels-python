# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

- `LatestValueCache` now takes an optional `key` function, which returns the key for each incoming message, and the latest value for each key is cached and can be retrieved separately.  

- `LatestValueCache` got a new `clear` method that clears the latest value.  When an optional `key` argument is specified, it clears the value only for that key.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
