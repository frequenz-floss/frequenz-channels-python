# Frequenz channels Release Notes

## Summary

This is the first releasse candidate for version 1.0. It includes few new features and a lot of cleanups and API improvements and polishing. Because of this, there are a lot of breaking changes too, but they should be easy to fix, as they ae mostly renames and reorganizations.

We hope this is the final pre-release before the final 1.0 release, and we don't expect to introduce any further breaking changes. Because of this we encourage you to test it and report any issues you find. You can also use a version constraint like `>= 1.0.0-rc.1, < 2.0.0` as the final version should be compatible.

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

* `Receiver`

  - The `map()` function now takes a positional-only argument, if you were using `receiver.map(call=fun)` you should replace it with `receiver.map(func)`.

* `SelectError` now inherits from `channels.Error` instead of `BaseException`, so you should be able to catch it with `except Exception:` or `except channels.Error:`.

* `Selected`

  - The `value` property was renamed to `message`.
  - `was_stopped` is now a property, you need to replace `selected.was_stopped()` with `selected.was_stopped`.

* `Sender`

  - The `send` method now takes a positional-only argument, if you were using `sender.send(msg=message)` you should replace it with `sender.send(message)`.

* `Timer` and support classes

  - Moved from `frequenz.channels.util` to `frequenz.channels.timer`.

* All exceptions that took `Any` as the `message` argument now take `str` instead.

  If you were passing a non-`str` value to an exception, you should convert it using `str(value)` before passing it to the exception.

* The following symbols were moved to the top-level `frequenz.channels` package:

  - `Selected`
  - `SelectError`
  - `UnhandledSelectedError`
  - `select`
  - `selected_from`

### Removals

* `Bidirectional`

  This channel was removed as it is not recommended practice and was a niche use case. If you need to use it, you can set up two channels or copy the `Bidirectional` class from the previous version to your project.

* `Merge`

  Replaced by the new `merge()` function. When replacing `Merge` with `merge()` please keep in mind that this new function will raise a `ValueError` if no receivers are passed to it.

  Please note that the old `Merge` class is still also available but it was renamed to `Merger` to avoid confusion with the new `merge()` function, but it is only present for typing reasons and should not be used directly.

* `MergeNamed`

  This class was redundant, use either the new `merge()` function or `select()` instead.

* `Peekable`

  This class was removed because it was merely a shortcut to a receiver that caches the last message received. It did not fit the channel abstraction well and was infrequently used.

  You can replace it with a task that receives and retains the last message.

* `Broadcast.new_peekable()`

  This was removed alongside `Peekable`.

* `Receiver.into_peekable()`

  This was removed alongside `Peekable`.

* `ReceiverInvalidatedError`

  This was removed alongside `Peekable` (it was only raised when using a `Receiver` that was converted into a `Peekable`).

* `SelectErrorGroup` was removed, a Python built-in `BaseExceptionGroup` is raised instead in case of unexpected errors while finalizing a `select()` loop, which will be automatically converted to a simple `ExceptionGroup` when no exception in the groups is a `BaseException`.

- `Timer`:

  - `periodic()` and `timeout()`: The names proved to be too confusing, please use `Timer()` and pass a missing ticks policy explicitly instead. In general you can update your code by doing:

    * `Timer.periodic(interval)` / `Timer.periodic(interval, skip_missed_ticks=True)` -> `Timer(interval, TriggerAllMissed())`
    * `Timer.periodic(interval, skip_missed_ticks=False)` -> `Timer(interval, SkipMissedAndResync())`
    * `Timer.timeout(interval)` -> `Timer(interval, SkipMissedAndDrift())`

* `util`

  The entire `util` package was removed and its symbols were either moved to the top-level package or to their own public modules (as noted above).

 ## New Features

* A new User's Guide was added to the documentation and the documentation was greately improved in general.

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

## Improvements

* `Receiver`, `merge`/`Merger`, `Error` and its derived classes now use a covariant generic type, which allows the generic type to be broader than the actual type.

* `Sender` now uses a contravariant generic type, which allows the generic type to be narrower than the required type.

*  `ChannelError` is now generic, so when accessing the `channel` attribute, the type of the channel is preserved.

* The generated documentation / website was greatly improved, both in content and looks.

## Bug Fixes

* `Timer`: Fix bug that was causing calls to `reset()` to not reset the timer, if the timer was already being awaited.
