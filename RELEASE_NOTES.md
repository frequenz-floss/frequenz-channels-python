# Frequenz channels Release Notes

## Summary

This will probably be the last minor release of v1. It deprecates everything that will be removed in v2.0.0.

## Upgrading

- `frequenz-core >= 1.6.0, < 2` is now a runtime dependency. It provides the utilities this project uses to deprecate symbols following the Frequenz deprecations guide.

- The minimum `typing-extensions` version is now 4.16.0. `frequenz-core` requires 4.13.0, and the new `buffer_size` argument needs the `sentinel` type added in 4.16.0.

- `frequenz.channels.Anycast`, deprecated since v1.12.0, will be removed in a future version, not necessarily the next major one. Its deprecation warning now recommends copying its code into your project if you need it, or [opening an issue](https://github.com/frequenz-floss/frequenz-channels-python/issues) if you think it should stay in the library.

- `watchfiles` versions up to 1.3 are now allowed.

- `frequenz.channels.experimental.GroupingLatestValueCache` and its type variables `DefaultT`, `HashableT` and `ValueT_co`, and `frequenz.channels.experimental.RelaySender` are deprecated and will be removed in v2.0.0. There is no replacement in this library: copy their code into your project if you need them, or [open an issue](https://github.com/frequenz-floss/frequenz-channels-python/issues) if you think they should stay.

- `frequenz.channels.experimental.NopReceiver` and `frequenz.channels.experimental.WithPrevious` are deprecated. Import them from `frequenz.channels` instead; they are the same objects, so only the import changes. The old names will be removed in v2.0.0.

- The deprecation warning of `frequenz.channels.experimental.OptionalReceiver` now points at `frequenz.channels.NopReceiver`. Use the receiver itself, or a `NopReceiver` when there is none.

- `frequenz.channels.timer.Timer` was renamed to `MonotonicTimer`, to make clear it uses the event loop's monotonic clock and to free the name `Timer` for a wall clock timer in a later version. `Timer` still works as a deprecated alias and will be removed in v2.0.0. The change is mechanical: replace `Timer` with `MonotonicTimer` in imports and uses.

- The `limit` argument of `BroadcastChannel()` and `BroadcastSender.subscribe()` is deprecated and will be removed in v2.0.0. Use the new `buffer_size` argument instead. It does the same, but its name says what is limited: the number of messages each receiver can hold. `buffer_size` is keyword-only. A call that passes both `limit` and `buffer_size` raises a `TypeError`. Passing `warn_on_overflow` by position is deprecated too, because the new form only accepts it by keyword: pass it by keyword. v2.0.0 will also make `resend_latest` keyword-only, so pass it by keyword too. `Broadcast` and `Anycast` are not changed.

- A `BroadcastChannel`, or a `Broadcast` created with `auto_close=True`, no longer closes when a message is sent while it has no receivers.  `send()` now drops the message and raises a `NoReceiversError`, a `SenderError` without a cause.  The channel stays open: `subscribe()` keeps working, and sending works again once a new receiver is attached.

- Code that waited for such a channel to close after a send without receivers, for example by checking for a `ChannelClosedError` cause or for `is_closed`, should catch `NoReceiversError` instead.  It can then stop sending, or close all of the channel's senders to close the channel.

- An experimental `Pipe` now closes its sender when its receiver stops.  Before, it left the sender open.

- When sending fails with a `SenderError`, for example because the sender's `BroadcastChannel` has no receivers, a `Pipe` now closes both its sender and its receiver, and logs the error: a `NoReceiversError` as a warning, and any other error with its traceback.  Before, the pipe stopped but left both open.

- `Pipe.stop()` still leaves a pipe's sender and receiver open.  So does any exception while receiving, other than the receiver stopping, and any exception from sending that isn't a `SenderError`.

- To keep a `Pipe` running after a `SenderError`, pass `close_pipe_on_send_error=False`.  It then drops the message, keeps sending the messages that follow, and logs a `NoReceiversError` at debug level.

- Give a `Pipe` a clone of its sender if you still need to send after the pipe stops on its own.

- `BroadcastSender.clone()` now raises a `SenderClosedError` if the sender is closed, and a `SenderError` if the channel is closed, like `send()` and `subscribe()` do.  Clone a sender before closing it, or catch `SenderError`.

- `BroadcastSender.subscribe()` now uses the `limit` and `warn_on_overflow` values the `BroadcastChannel` was created with as defaults, instead of `50` and `True`.  Pass `limit=50, warn_on_overflow=True` to keep the old values.

- Call `BroadcastReceiver.close()` from the thread that runs the event loop of the channel's receivers.  From another thread, tasks waiting on any receiver of the channel might not wake up.  If asyncio debug mode is on and a task is waiting, `close()` also raises a `RuntimeError`, and the waiting tasks stay stuck.  Use `loop.call_soon_threadsafe(receiver.close)` instead.

- `Broadcast` is now a deprecated alias of the class behind `BroadcastChannel`.  The `DeprecationWarning` is now emitted when `Broadcast` is imported or accessed from `frequenz.channels`, including by `from frequenz.channels import *`, instead of each time a channel is created, and type checkers no longer report it as deprecated.  Please use `BroadcastChannel` instead.

- This package now depends on `frequenz-core >= 1.6.0, < 2`, and needs `typing-extensions >= 4.13.0`.

## New Features

- `NopReceiver` and `WithPrevious` are now stable, and available from `frequenz.channels`.

- `NoReceiversError` is a new `SenderError`.  An open sender of a `BroadcastChannel`, or of a `Broadcast` created with `auto_close=True`, raises it from `send()` while the channel is open but has no receivers.  The message is dropped, but with `resend_latest=True`, new receivers still get it if it is the last message sent and it isn't `None`.

- `BroadcastSender.has_receivers` and `BroadcastReceiver.has_senders` tell whether the other side of a broadcast channel is still there, so producers can stop producing messages that nobody would receive.  A sender that was garbage-collected without being closed still counts.

## Bug Fixes

- `BroadcastChannel()` no longer emits the deprecation warning of `Broadcast`, which it uses internally. You were getting a warning about a class you never used.

- `OneshotReceiver.close()` no longer raises `NotImplementedError`. It now works like in the other receivers: a message sent before closing can still be received, and after that receiving raises `ReceiverStoppedError`. The sender can still send, but its message is discarded.

- Creating a broadcast receiver with a `buffer_size` (or `limit`) of 0 now raises a `ValueError`, from `BroadcastChannel()` and `BroadcastSender.subscribe()`. Before, the first message sent to it raised an `IndexError`, after other receivers might have got the message already.

- Docstrings now use absolute cross-references to public paths instead of relative ones. Relative cross-references are expanded from the module where an object is defined since mkdocstrings-python 2.0.9, which broke some links, and projects rendering docstrings inherited from this library needed `relative_crossrefs: true` for them to work at all. See [frequenz-repo-config-python#655](https://github.com/frequenz-floss/frequenz-repo-config-python/issues/655) for details.

- Closing a broadcast receiver now wakes up tasks waiting for messages on it, instead of leaving them blocked until the next message arrived or the channel was closed.

- Closing a broadcast receiver now drops the messages left in its buffer, so it is no longer reported as ready.  So `select()` no longer reports it as stopped over and over, and no longer fails with a `SelectError` for a `filter()` on it.

- Sending to or closing a broadcast channel no longer raises `RuntimeError: Event loop is closed` when a receiver was left waiting on an event loop that has since been closed.

- Creating a `BroadcastChannel` no longer emits a deprecation warning telling users to use `BroadcastChannel` instead.
