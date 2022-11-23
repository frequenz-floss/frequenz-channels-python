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

* The public API surface has been reduced considerably to make it more clear
  where to import symbols.  You should update your imports.  The new symbol
  locations are:

  * `frequenz.channels.Anycast`
  * `frequenz.channels.Broadcast`
  * `frequenz.channels.Anycast`
  * `frequenz.channels.Bidirectional`
  * `frequenz.channels.Broadcast`
  * `frequenz.channels.Peekable`
  * `frequenz.channels.Receiver`
  * `frequenz.channels.Sender`
  * `frequenz.channels.util.Merge`
  * `frequenz.channels.util.MergeNamed`
  * `frequenz.channels.util.FileWatcher`
  * `frequenz.channels.util.Select`
  * `frequenz.channels.util.Timer`

* The class `BufferedReceiver` was removed because the interface was really
  intended for channel implementations. Users are not supposed to enqueue
  messages to receiver but just receive from them. If you used it you can
  implement it yourself.

* The class `BidirectionalHandle` was moved to `Bidirectional.Handle`.

* The class `EventType` was moved to `FileWatcher.EventType`.

## New Features

* Python 3.11 is now supported!

## Bug Fixes

* [`Broadcast`] receivers now get cleaned up once they go out of scope.

* [`Timer`] now returns [timezone-aware] `datetime` objects using UTC as
  timezone.

[`Broadcast`]: https://frequenz-floss.github.io/frequenz-channels-python/v0.11/reference/frequenz/channels/#frequenz.channels.Broadcast
[`Timer`]: https://frequenz-floss.github.io/frequenz-channels-python/v0.11/reference/frequenz/channels/#frequenz.channels.Timer
[timezone-aware]: https://docs.python.org/3/library/datetime.html#aware-and-naive-objects
