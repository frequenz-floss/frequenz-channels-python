# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

* `Anycast`

  - `__init__`: The `maxsize` argument was renamed to `limit` and made keyword-only and a new keyword-only `name` argument was added.

    You should instantiate using `Anycast(name=..., limit=...)` (or `Anycast(name=...)` if the default `limit` is enough) instead of `Anycast(...)` or `Anycast(maxsize=...)`.

  - `new_sender` and `new_receiver`: They now return a base `Sender` and `Receiver` class (respectively) instead of a channel-specific `Sender` or `Receiver` subclass.

    This means users now don't have access to the internals to the channel-specific `Sender` and `Receiver` subclasses.

* `Broadcast`

  - `__init__`: The `name` argument was made optional and keyword-only; `resend_latest` was also made keyword-only. If a `name` is not specified, it will be generated from the `id()` of the instance.

    You should instantiate using `Broadcast(name=name, resend_latest=resend_latest)` (or `Broadcast()` if the defaults are enough) instead of `Broadcast(name)` or `Broadcast(name, resend_latest)`.

  - `new_receiver`: The `maxsize` argument was renamed to `limit` and made keyword-only; the `name` argument was also made keyword-only. If a `name` is not specified, it will be generated from the `id()` of the instance instead of a random UUID.

    You should use `.new_receiver(name=name, limit=limit)` (or `.new_receiver()` if the defaults are enough) instead of `.new_receiver(name)` or `.new_receiver(name, maxsize)`.

  - `new_sender` and `new_receiver` now return a base `Sender` and `Receiver` class (respectively) instead of a channel-specific `Sender` or `Receiver` subclass.

    This means users now don't have access to the internals to the channel-specific `Sender` and `Receiver` subclasses.

* `Event`

  - `__init__`: The `name` argument was made keyword-only. The default was changed to a more readable version of `id(self)`.

    You should instantiate using `Event(name=...)` instead of `Event(...)`.

  - Moved from `frequenz.channels.util` to `frequenz.channels.event`.

* `FileWatcher`

  - Moved from `frequenz.channels.util` to `frequenz.channels.file_watcher`.

  - Support classes are no longer nested inside `FileWatcher`. They are now top-level classes within the new `frequenz.channels.file_watcher` module (e.g., `frequenz.channels.util.FileWatcher.EventType` -> `frequenz.channels.file_watcher.EventType`, `frequenz.channels.util.FileWatcher.Event` -> `frequenz.channels.file_watcher.Event`).

* `Timer` and support classes

  - Moved from `frequenz.channels.util` to `frequenz.channels.timer`.

* All exceptions that took `Any` as the `message` argument now take `str` instead.

  If you were passing a non-`str` value to an exception, you should convert it using `str(value)` before passing it to the exception.

* The following symbols were moved to the top-level `frequenz.channels` package:

  - `Selected`
  - `SelectError`
  - `SelectErrorGroup`
  - `UnhandledSelectedError`
  - `select`
  - `selected_from`

### Removals

* `Bidirectional`

  This channel was removed as it is not recommended practice and was a niche use case. If you need to use it, you can set up two channels or copy the `Bidirectional` class from the previous version to your project.

* `Merge`

  Replaced by the new `merge()` function. When replacing `Merge` with `merge()` please keep in mind that this new function will raise a `ValueError` if no receivers are passed to it.

* `MergeNamed`

  This class was redundant, use either the new `merge()` function or `select()` instead.

* `Peekable`

  This class was removed because it was merely a shortcut to a receiver that caches the last value received. It did not fit the channel abstraction well and was infrequently used.

  You can replace it with a task that receives and retains the last value.

* `Broadcast.new_peekable()`

  This was removed alongside `Peekable`.

* `Receiver.into_peekable()`

  This was removed alongside `Peekable`.

* `ReceiverInvalidatedError`

  This was removed alongside `Peekable` (it was only raised when using a `Receiver` that was converted into a `Peekable`).

* `util`

  The entire `util` package was removed and its symbols were either moved to the top-level package or to their own public modules (as noted above).

 ## New Features

* A new `merge()` function was added to replace `Merge`.

* `Anycast`

  - The following new read-only properties were added:

    - `name`: The name of the channel.
    - `limit`: The maximum number of messages that can be sent to the channel.
    - `is_closed`: Whether the channel is closed.

  - A more useful implementation of `__str__ and `__repr__` were added for the channel and its senders and receivers.

  - A warning will be logged if senders are blocked because the channel buffer is full.

* `Bidirectional`

  - The following new read-only properties were added:

    - `name`: The name of the channel (read-only).
    - `is_closed`: Whether the channel is closed (read-only).

  - A more useful implementation of `__str__ and `__repr__` were added for the channel and the client and service handles.

* `Broadcast`

  - The following new read-only properties were added:

    - `name`: The name of the channel.
    - `is_closed`: Whether the channel is closed.

  - A more useful implementation of `__str__ and `__repr__` were added for the channel and the client and service handles.

* `FileWatcher`

  - A more useful implementation of `__str__ and `__repr__` were added.

* `Peekable`

  - A more useful implementation of `__str__ and `__repr__` were added.

* `Receiver`

  - `map()`: The returned map object now has a more useful implementation of `__str__ and `__repr__`.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
