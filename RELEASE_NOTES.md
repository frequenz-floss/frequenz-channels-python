# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

- `BroadcastChannel()` and `BroadcastSender.subscribe()` now take everything but the name by keyword: `resend_latest`, `buffer_size` and `warn_on_overflow`.  The deprecated `limit` is keyword-only too, so a call that passed `limit` or any other option by position fails with a `TypeError`.  Pass them by keyword, as v1.13.0 recommends.

- The `repr()` of a `BroadcastReceiver` shows its `buffer_size` instead of `limit`.

- A `BroadcastChannel`, or a `Broadcast` created with `auto_close=True`, no longer closes when a message is sent while it has no receivers.  `send()` now drops the message and raises a `SenderHasNoReceiversError`, a `SenderError` without a cause.  The channel stays open: `subscribe()` keeps working, and sending works again once a new receiver is attached.

- Code that waited for such a channel to close after a send without receivers, for example by checking for a `ChannelClosedError` cause or for `is_closed`, should catch `SenderHasNoReceiversError` instead.  It can then stop sending, or close all of the channel's senders to close the channel.

- An experimental `Pipe` now closes its sender when its receiver stops.  Before, it left the sender open.

- When sending fails with a `SenderError`, for example because the sender's `BroadcastChannel` has no receivers, a `Pipe` now closes both its sender and its receiver, and logs the error: a `SenderHasNoReceiversError` as a warning, and any other error with its traceback.  Before, the pipe stopped but left both open.

- `Pipe.stop()` still leaves a pipe's sender and receiver open.  So does any exception while receiving, other than the receiver stopping, and any exception from sending that isn't a `SenderError`.

- To keep a `Pipe` running after a `SenderError`, pass `close_pipe_on_send_error=False`.  It then drops the message, keeps sending the messages that follow, and logs a `SenderHasNoReceiversError` at debug level.

- Give a `Pipe` a clone of its sender if you still need to send after the pipe stops on its own.

- `BroadcastSender.clone()` now raises a `SenderClosedError` if the sender is closed, and a `SenderError` if the channel is closed, like `send()` and `subscribe()` do.  Clone a sender before closing it, or catch `SenderError`.

- `BroadcastSender.subscribe()` now uses the `buffer_size` and `warn_on_overflow` values the `BroadcastChannel` was created with as defaults, instead of `50` and `True`.  Pass `buffer_size=50, warn_on_overflow=True` to keep the old values.

- Call `BroadcastReceiver.close()` from the thread that runs the event loop of the channel's receivers.  From another thread, tasks waiting on any receiver of the channel might not wake up.  If asyncio debug mode is on and a task is waiting, `close()` also raises a `RuntimeError`, and the waiting tasks stay stuck.  Use `loop.call_soon_threadsafe(receiver.close)` instead.

- `Broadcast` is now a deprecated alias of the class behind `BroadcastChannel`.  The `DeprecationWarning` is now emitted when `Broadcast` is imported or accessed from `frequenz.channels`, including by `from frequenz.channels import *`, instead of each time a channel is created, and type checkers no longer report it as deprecated.  Please use `BroadcastChannel` instead.

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

- `TransientSenderError` is a new `SenderError` for errors after which the sender and its channel can still be used: only the message that failed wasn't sent.  Catch it before `SenderError` to tell it apart from the errors that make a sender unusable.

- `SenderHasNoReceiversError` is a new `TransientSenderError`.  An open sender of a `BroadcastChannel`, or of a `Broadcast` created with `auto_close=True`, raises it from `send()` while the channel is open but has no receivers.  The message is dropped, but with `resend_latest=True`, new receivers still get it if it is the last message sent and it isn't `None`.  The channel stays open, so sending works again once a receiver subscribes.

- `BroadcastSender.has_receivers` and `BroadcastReceiver.has_senders` tell whether the other side of a broadcast channel is still there, so producers can stop producing messages that nobody would receive.  A sender that was garbage-collected without being closed still counts.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->

- Closing a broadcast receiver now wakes up tasks waiting for messages on it, instead of leaving them blocked until the next message arrived or the channel was closed.

- Closing a broadcast receiver now drops the messages left in its buffer, so it is no longer reported as ready.  So `select()` no longer reports it as stopped over and over, and no longer fails with a `SelectError` for a `filter()` on it.

- Sending to or closing a broadcast channel no longer raises `RuntimeError: Event loop is closed` when a receiver was left waiting on an event loop that has since been closed.
