# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

- A `BroadcastChannel`, or a `Broadcast` created with `auto_close=True`, no longer closes when a message is sent while it has no receivers.  `send()` now drops the message and raises a `NoReceiversError`, a `SenderError` without a cause.  The channel stays open: `subscribe()` keeps working, and sending works again once a new receiver is attached.

- Code that waited for such a channel to close after a send without receivers, for example by checking for a `ChannelClosedError` cause or for `is_closed`, should catch `NoReceiversError` instead.  It can then stop sending, or close all of the channel's senders to close the channel.

- An experimental `Pipe` now closes its sender when its receiver stops.  When sending fails with a `SenderError`, for example because the sender's `BroadcastChannel` has no receivers, it closes its receiver too.  It also logs the error: a `NoReceiversError` as a warning, and any other error with its traceback.  Before, the pipe stopped but left both open.  `Pipe.stop()` still leaves both open.

- Give a `Pipe` a clone of its sender if you still need to send after the pipe stops on its own.

- `BroadcastSender.clone()` now raises a `SenderClosedError` if the sender is closed, and a `SenderError` if the channel is closed, like `send()` and `subscribe()` do.

- `BroadcastSender.subscribe()` now uses the `limit` and `warn_on_overflow` values the `BroadcastChannel` was created with as defaults, instead of `50` and `True`.

- `Broadcast` is now a deprecated alias of the class behind `BroadcastChannel`.  The `DeprecationWarning` is now emitted when `Broadcast` is imported or accessed from `frequenz.channels`, instead of each time a channel is created, and type checkers no longer report it as deprecated.  Please use `BroadcastChannel` instead.

- This package now depends on `frequenz-core >= 1.6.0, < 2`, and needs `typing-extensions >= 4.13.0`.

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

- `NoReceiversError` is a new `SenderError`.  An open sender of a `BroadcastChannel`, or of a `Broadcast` created with `auto_close=True`, raises it from `send()` while the channel is open but has no receivers.  The message is dropped.  With `resend_latest=True`, new receivers get the last message that was sent successfully instead.

- `BroadcastSender.has_receivers` and `BroadcastReceiver.has_senders` tell whether the other side of a broadcast channel is still there, so producers can stop producing messages that nobody would receive.  A sender dropped without being closed still counts.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->

- Docstrings now use absolute cross-references to public paths instead of relative ones. Relative cross-references are expanded from the module where an object is defined since mkdocstrings-python 2.0.9, which broke some links, and projects rendering docstrings inherited from this library needed `relative_crossrefs: true` for them to work at all. See [frequenz-repo-config-python#655](https://github.com/frequenz-floss/frequenz-repo-config-python/issues/655) for details.

- Closing a broadcast receiver now wakes up tasks waiting for messages on it, instead of leaving them blocked until the next message arrived or the channel was closed.

- A closed broadcast receiver is no longer reported as ready while messages are left in its buffer.  So `select()` reports it as stopped once instead of over and over, and no longer fails with a `SelectError` for a `filter()` on it.

- Sending to or closing a broadcast channel no longer raises `RuntimeError: Event loop is closed` when a receiver was left waiting on an event loop that has since been closed.

- Creating a `BroadcastChannel` no longer emits a deprecation warning telling users to use `BroadcastChannel` instead.
