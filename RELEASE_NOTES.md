# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

- `frequenz-core >= 1.6.0, < 2` is now a runtime dependency. It provides the utilities this project uses to deprecate symbols following the Frequenz deprecations guide.

- The minimum `typing-extensions` version is now 4.13.0, which `frequenz-core` requires.

- `frequenz.channels.experimental.Pipe` is deprecated and will be removed in v2.0.0. Use `frequenz.channels.Pipe` instead, but check how your code closes the sender and the receiver of the pipe first, as the two behave differently:

    - When its receiver stops, the new `Pipe` closes its sender. The experimental one stops and leaves the sender open.
    - When sending fails with a `SenderError`, the new `Pipe` logs the error and closes both its sender and its receiver by default. The experimental one lets the exception end its task and leaves both open.
    - With `close_pipe_on_send_error=False`, the new `Pipe` drops the message that failed and keeps forwarding the next ones. This doesn't bring back the behavior of the experimental one.
    - `stop()` leaves both ends open in both.

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

- `Pipe` is now available in `frequenz.channels`. It forwards all the messages from a receiver to a sender, like `frequenz.channels.experimental.Pipe`, but it also closes its ends: when its receiver stops it closes its sender, and when sending fails with a `SenderError` it closes its sender and its receiver, unless you pass `close_pipe_on_send_error=False`, in which case it drops the message and keeps going. See the `Pipe` documentation for what the pipe leaves open and who has to close it.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->

- `BroadcastChannel()` no longer emits the deprecation warning of `Broadcast`, which it uses internally. You were getting a warning about a class you never used.

- Docstrings now use absolute cross-references to public paths instead of relative ones. Relative cross-references are expanded from the module where an object is defined since mkdocstrings-python 2.0.9, which broke some links, and projects rendering docstrings inherited from this library needed `relative_crossrefs: true` for them to work at all. See [frequenz-repo-config-python#655](https://github.com/frequenz-floss/frequenz-repo-config-python/issues/655) for details.
