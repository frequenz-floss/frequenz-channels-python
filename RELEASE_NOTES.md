# Frequenz Channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

* The `Sender.send()` method now `raise`s a `SenderError` instead of returning `False`. The `SenderError` will typically have a `ChannelClosedError` and the underlying reason as a chained exception.

## New Features

* New exceptions were added:

  * `Error`: A base exception from which all exceptions from this library inherit.

  * `SendError`: Raised for errors when sending messages.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
