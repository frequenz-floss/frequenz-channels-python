# Frequenz Channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

* The `Sender.send()` method now `raise`s a `SenderError` instead of returning `False`. The `SenderError` will typically have a `ChannelClosedError` and the underlying reason as a chained exception.

* The `Receiver.ready()` method (and related `receive()` and `__anext__` when used as an async iterator) now `raise`s a `ReceiverError` and in particular a `ReceiverStoppedError` when the receiver has no more messages to receive.

  `Receiver.consume()` doesn't raise any exceptions.

  Receivers raising `EOFError` now raise `ReceiverError` instead.

* For channels which senders raise an error when the channel is closed or which receivers stop receiving when the channel is closed, the `SenderError` and `ReceiverStoppedError` are chained with a `__cause__` that is a `ChannelClosedError` with the channel that was closed.

* `ChannelClosedError` now requires the argument `channel` (before it was optional).

## New Features

* New exceptions were added:

  * `Error`: A base exception from which all exceptions from this library inherit.

  * `SendError`: Raised for errors when sending messages.

  * `ReceiverError`: Raised for errors when receiving messages.

  * `ReceiverClosedError`: Raised when a receiver don't have more messages to receive.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
