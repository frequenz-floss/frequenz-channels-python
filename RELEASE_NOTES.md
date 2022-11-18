# Frequenz Channels Release Notes

## Summary

The project has a new home!

https://frequenz-floss.github.io/frequenz-channels-python/

For now the documentation is pretty scarce but we will be improving it with
time.

## Upgrading (breaking changes)

* You need to make sure to use [timezone-aware] `datetime` objects when using
  the timestamp returned by [`Timer`], Otherwise you will get an exception.

* Channels methods `get_receiver()` and `get_sender()` have been renamed to
  `new_receiver()` and `new_sender()` respectively. This is to make it more
  clear that new objects are being created.

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

## Bug Fixes

* [`Broadcast`] receivers now get cleaned up once they go out of scope.

* [`Timer`] now returns [timezone-aware] `datetime` objects using UTC as
  timezone.

[`Broadcast`]: https://frequenz-floss.github.io/frequenz-channels-python/v0.11/reference/frequenz/channels/#frequenz.channels.Broadcast
[`Timer`]: https://frequenz-floss.github.io/frequenz-channels-python/v0.11/reference/frequenz/channels/#frequenz.channels.Timer
[timezone-aware]: https://docs.python.org/3/library/datetime.html#aware-and-naive-objects
