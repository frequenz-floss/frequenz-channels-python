# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

- `BroadcastChannel()` and `BroadcastSender.subscribe()` now take only the name by position.  `resend_latest` (only in `BroadcastChannel()`), `buffer_size` and `warn_on_overflow` must be passed by keyword.  A call that passes any of them by position fails with a `TypeError`.  v1.13.0 already deprecates passing `warn_on_overflow` by position, but it doesn't warn about `resend_latest`, so look for calls like `BroadcastChannel("name", True)` and pass it by keyword.

- The deprecated `limit` argument of `BroadcastChannel()` and `BroadcastSender.subscribe()` is removed.  Use `buffer_size` instead, which exists since v1.13.0, so you can migrate before upgrading.  `Broadcast.new_receiver()` still takes `limit`.

- The deprecated `frequenz.channels.timer.Timer` is removed.  Use `MonotonicTimer` instead, which exists since v1.13.0, so you can migrate before upgrading.  The name `Timer` will be used for a wall clock timer in a later version.

- `Anycast` is removed.  There is no replacement: copy its code into your project if you still need it.

- `frequenz.channels.experimental.GroupingLatestValueCache` is removed, together with its type variables `DefaultT`, `HashableT` and `ValueT_co`.  Copy its code into your project if you still need it, or open an issue if you think it should stay in the library.

- `frequenz.channels.experimental.RelaySender` is removed.  Copy its code into your project if you still need it, or open an issue if you think it should stay in the library.

- `frequenz.channels.experimental.OptionalReceiver` is removed.  Use the receiver itself, or `frequenz.channels.NopReceiver` when there is none.  `NopReceiver` exists since v1.13.0, so you can migrate before upgrading.

- `WithPrevious` and `NopReceiver` are no longer available from `frequenz.channels.experimental`.  Import them from `frequenz.channels`, where they are available since v1.13.0, so you can migrate before upgrading.

- The deprecated `async close()` method of `Broadcast` is removed.  Use `aclose()` instead, which exists since v1.8.0, so you can migrate before upgrading.  It also works with `contextlib.aclosing()`.

- The `repr()` of a `BroadcastReceiver` shows its `buffer_size` instead of `limit`.

- A `BroadcastChannel`, or a `Broadcast` created with `auto_close=True`, no longer closes when a message is sent while it has no receivers.  `send()` now drops the message and raises a `SenderHasNoReceiversError`, a `SenderError` without a cause.  The channel stays open: `subscribe()` keeps working, and sending works again once a new receiver is attached.

- Code that waited for such a channel to close after a send without receivers, for example by checking for a `ChannelClosedError` cause or for `is_closed`, should catch `SenderHasNoReceiversError` instead.  It can then stop sending, or close all of the channel's senders to close the channel.

- `frequenz.channels.experimental.Pipe` is deprecated and will be removed in v3.0.0.  Use the new `frequenz.channels.Pipe` instead, but check how your code closes the sender and the receiver of the pipe first, as the two behave differently:

    - When its receiver stops, the new `Pipe` closes its sender.  The experimental one stops and leaves the sender open.
    - When sending fails with a `SenderError` that isn't a `TransientSenderError`, the new `Pipe` logs the error and closes both its sender and its receiver by default.  The experimental one lets the exception end its task and leaves both open.
    - When sending fails with a `TransientSenderError`, like a `SenderHasNoReceiversError`, the new `Pipe` logs it, drops the message and keeps forwarding.  The experimental one lets the exception end its task.
    - With `close_pipe_on_send_error=False`, the new `Pipe` also drops the message that failed with any other `SenderError` and keeps forwarding the next ones.  This doesn't bring back the behavior of the experimental one.
    - `stop()` leaves both ends open in both.

- `BroadcastSender.clone()` now raises a `SenderClosedError` if the sender is closed, and a `SenderError` if the channel is closed, like `send()` and `subscribe()` do.  Clone a sender before closing it, or catch `SenderError`.

- `BroadcastSender.subscribe()` now uses the `buffer_size` and `warn_on_overflow` values the `BroadcastChannel` was created with as defaults, instead of `50` and `True`.  Pass `buffer_size=50, warn_on_overflow=True` to keep the old values.

- Call `BroadcastReceiver.close()` from the thread that runs the event loop of the channel's receivers.  From another thread, tasks waiting on any receiver of the channel might not wake up.  If asyncio debug mode is on and a task is waiting, `close()` also raises a `RuntimeError`, and the waiting tasks stay stuck.  Use `loop.call_soon_threadsafe(receiver.close)` instead.

- `Receiver.close()` is now an abstract method, so a custom `Receiver` subclass that doesn't implement it can't be instantiated anymore.  Before, calling it raised a `NotImplementedError`.  All the receivers in this library implement it already.  Add a `close()` method to your own receivers; the same implementation works on v1, so your code can support both major versions.

## New Features

- `TransientSenderError` is a new `SenderError` for errors after which the sender and its channel can still be used: only the message that failed wasn't sent.  Catch it before `SenderError` to tell it apart from the errors that make a sender unusable.

- `SenderHasNoReceiversError` is a new `TransientSenderError`.  An open sender of a `BroadcastChannel`, or of a `Broadcast` created with `auto_close=True`, raises it from `send()` while the channel is open but has no receivers.  The message is dropped, but with `resend_latest=True`, new receivers still get it if it is the last message sent and it isn't `None`.  The channel stays open, so sending works again once a receiver subscribes.

- `Pipe` is now available in `frequenz.channels`.  It forwards all the messages from a receiver to a sender, like `frequenz.channels.experimental.Pipe`, but it also closes its ends: when its receiver stops it closes its sender, and when sending fails with a `SenderError` that isn't a `TransientSenderError` it closes its sender and its receiver, unless you pass `close_pipe_on_send_error=False`, in which case it drops the message and keeps going.  When sending fails with a `TransientSenderError`, like a `SenderHasNoReceiversError`, it logs it, drops the message and keeps forwarding, whatever `close_pipe_on_send_error` says.  See the `Pipe` documentation for what the pipe leaves open and who has to close it.

- `BroadcastSender.has_receivers` and `BroadcastReceiver.has_senders` tell whether the other side of a broadcast channel is still there, so producers can stop producing messages that nobody would receive.  A sender that was garbage-collected without being closed still counts.

## Bug Fixes

- Closing a broadcast receiver now wakes up tasks waiting for messages on it, instead of leaving them blocked until the next message arrived or the channel was closed.

- Closing a broadcast receiver now drops the messages left in its buffer, so it is no longer reported as ready.  So `select()` no longer reports it as stopped over and over, and no longer fails with a `SelectError` for a `filter()` on it.

- Sending to or closing a broadcast channel no longer raises `RuntimeError: Event loop is closed` when a receiver was left waiting on an event loop that has since been closed.
