# Frequenz Channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

* The `Sender.send()` method now `raise`s a `SenderError` instead of returning `False`. The `SenderError` will typically have a `ChannelClosedError` and the underlying reason as a chained exception.

* The `Receiver.ready()` method (and related `receive()` and `__anext__` when used as an async iterator) now `raise`s a `ReceiverError` and in particular a `ReceiverStoppedError` when the receiver has no more messages to receive.

  `Receiver.consume()` doesn't raise any exceptions.

  Receivers raising `EOFError` now raise `ReceiverInvalidatedError` instead.

* For channels which senders raise an error when the channel is closed or which receivers stop receiving when the channel is closed, the `SenderError` and `ReceiverStoppedError` are chained with a `__cause__` that is a `ChannelClosedError` with the channel that was closed.

* `ChannelClosedError` now requires the argument `channel` (before it was optional).

* Now exceptions are not raised in Receiver.ready() but in Receiver.consume() (receive() or the async iterator `anext`).

* `Select` constructor now takes a variable number of receivers:

  ```py
  select = Select(recv1, recv2)
  ```

* `Select.ready()` is now an async iterator and yields a set of receivers that are ready to be consumed. Receivers must be explicitly consumed and if a ready receiver is not consumed, the ready message won't be discarded by select any more, it will wait indefinitely until it is consumed.

  Example:

  ```py
  select = Select(recv1, recv2)
  async for ready_set in select.ready():
      if recv1 in ready_set:
          msg = recv1.consume()
	  # do whatever with msg, consume() can also raise an error as normal
      if recv2 in ready_set:
          msg = recv2.consume()
  ```

## New Features

* New exceptions were added:

  * `Error`: A base exception from which all exceptions from this library inherit.

  * `SendError`: Raised for errors when sending messages.

  * `ReceiverError`: Raised for errors when receiving messages.

  * `ReceiverClosedError`: Raised when a receiver don't have more messages to receive.

  * `ReceiverInvalidatedError`: Raised when a receiver was invalidated (for example it was converted into a `Peekable`).

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
