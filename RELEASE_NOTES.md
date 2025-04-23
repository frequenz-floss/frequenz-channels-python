# Frequenz channels Release Notes

## Summary

This release focuses on improving `async` patterns and flexibility in the channel's library.

## Upgrading

- Some minimal dependencies have been bumped, so you might need to adjust your dependencies accordingly.
- `Broadcast` and `Anycast` channels method `close()` was renamed to `aclose()` to follow Python's convention. With this change now channels can be used with the [`aclosing()`](https://docs.python.org/3/library/contextlib.html#contextlib.aclosing) context manager for example.

   The name `close()` is still available for backwards compatibility, but it will be removed in the next major release, so it is recommended to switch to `aclose()`.

## New Features

- Add a new `OptionalReceiver` class that wraps an optional underlying receiver, allowing for indefinite waiting when no receiver is set.
- Improve documentation of the `frequenz.channels.experimental.Pipe`
