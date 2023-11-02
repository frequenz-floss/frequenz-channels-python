# Frequenz channels Release Notes

## Summary

The `Timer` now can be started with a delay.

## Upgrading

* `Anycast`

  - `__init__`: The `maxsize` argument was renamed to `limit` and made keyword-only and a new optional, keyword-only `name` argument was added. If a `name` is not specified, it will be generated from the `id()` of the instance.

    You should instantiate using `Anycast(name=..., limit=...)` (or `Anycast()` if the defaults are enough) instead of `Anycast(...)` or `Anycast(maxsize=...)`.

* `Bidirectional`

  - The `client_id` and `service_id` arguments were merged into an optional, keyword-only `name`. If a `name` is not specified, it will be generated from the `id()` of the instance.

    You should instantiate using `Bidirectional(name=...)` (or `Bidirectional()` if the default name is enough) instead of `Bidirectional(..., ...)` or `Bidirectional(client_id=..., service_id=...)`.

  - `new_receiver`: The `maxsize` argument was renamed to `limit` and made keyword-only; the `name` argument was also made keyword-only. If a `name` is not specified, it will be generated from the `id()` of the instance instead of a random UUID.

    You should instantiate using `Broadcast(name=name, resend_latest=resend_latest)` (or `Broadcast()` if the defaults are enough) instead of `Broadcast(name)` or `Broadcast(name, resend_latest)`.

* `Broadcast`

  - `__init__`: The `name` argument was made optional and keyword-only; `resend_latest` was also made keyword-only. If a `name` is not specified, it will be generated from the `id()` of the instance.

    You should instantiate using `Broadcast(name=name, resend_latest=resend_latest)` (or `Broadcast()` if the defaults are enough) instead of `Broadcast(name)` or `Broadcast(name, resend_latest)`.

* `Event`

  - `__init__`: The `name` argument was made keyword-only. The default was changed to a more readable version of `id(self)`.

    You should instantiate using `Event(name=...)` instead of `Event(...)`.

* All exceptions that took `Any` as the `message` argument now take `str` instead.

  If you were passing a non-`str` value to an exception, you should convert it using `str(value)` before passing it to the exception.

## New Features

* `Anycast`

  - The following new read-only properties were added:

    - `name`: The name of the channel.
    - `limit`: The maximum number of messages that can be sent to the channel.
    - `is_closed`: Whether the channel is closed.

  - A more useful implementation of `__str__ and `__repr__` were added for the channel and its senders and receivers.

* `Bidirectional`

  - The following new read-only properties were added:

    - `name`: The name of the channel (read-only).
    - `is_closed`: Whether the channel is closed (read-only).

  - A more useful implementation of `__str__ and `__repr__` were added for the channel and the client and service handles.

* `Broadcast`

  - The following new read-only properties were added:

    - `name`: The name of the channel.
    - `latest`: The latest message sent to the channel.
    - `is_closed`: Whether the channel is closed.

  - A more useful implementation of `__str__ and `__repr__` were added for the channel and the client and service handles.

* `FileWatcher`

  - A more useful implementation of `__str__ and `__repr__` were added.

* `Merge`

  - A more useful implementation of `__str__ and `__repr__` were added.

* `MergeNamed`

  - A more useful implementation of `__str__ and `__repr__` were added.

* `Peekable`

  - A more useful implementation of `__str__ and `__repr__` were added.

* `Receiver`

  - `map()`: The returned map object now has a more useful implementation of `__str__ and `__repr__`.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
