# Frequenz channels Release Notes

## Summary

This release introduces the experimental `GroupingLatestValueCache` and includes a couple of bug fixes.

## New Features

- This release introduces the experimental `GroupingLatestValueCache`.  It is similar to the `LatestValueCache`, but accepts an additional key-function as an argument, which takes each incoming message and returns a key for that message.  The latest value received for each unique key gets cached and is available to look up on-demand through a `collections.abc.Mapping` interface.

## Bug Fixes

- Any open calls to `NopReceiver.ready()` now return as soon as the receiver is closed.

- The `__str__` representation of broadcast receivers now include the receiver's name.
