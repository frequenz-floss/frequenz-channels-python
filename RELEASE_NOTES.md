# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

- This release introduces the experimental `GroupingLatestValueCache`.  It is similar to the `LatestValueCache`, but accepts an additional key-function as an argument, which takes each incoming message and returns a key for that message.  The latest value received for each unique key gets cached and is available to look up on-demand through a `collections.abc.Mapping` interface.

## Bug Fixes

- Fix `NopReceiver.ready()` to properly terminate when receiver is closed.

- The `__str__` representation of broadcast receivers now include the receiver's name.
