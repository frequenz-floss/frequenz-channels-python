# Frequenz Channels Release Notes

## Summary

The project has a new home!

https://frequenz-floss.github.io/frequenz-channels-python/

For now the documentation is pretty scarce but we will be improving it with
time.

## Upgrading

* You need to make sure to use [timezone-aware] `datetime` objects when using
  the timestamp returned by [`Timer`], Otherwise you will get an exception.

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

## Bug Fixes

* [`Timer`] now returns [timezone-aware] `datetime` objects using UTC as
  timezone.


[`Timer`]: https://frequenz-floss.github.io/frequenz-channels-python/v0.11/reference/frequenz/channels/#frequenz.channels.Timer
[timezone-aware]: https://docs.python.org/3/library/datetime.html#aware-and-naive-objects
