# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

- `frequenz-core >= 1.6.0, < 2` is now a runtime dependency. It provides the utilities this project uses to deprecate symbols following the Frequenz deprecations guide.

- The minimum `typing-extensions` version is now 4.16.0. `frequenz-core` requires 4.13.0, and `CHANNEL_DEFAULT` needs the `sentinel` type added in 4.16.0.

- `frequenz.channels.experimental.GroupingLatestValueCache` and its type variables `DefaultT`, `HashableT` and `ValueT_co`, and `frequenz.channels.experimental.RelaySender` are deprecated and will be removed in v2.0.0. There is no replacement in this library: copy their code into your project if you need them, or [open an issue](https://github.com/frequenz-floss/frequenz-channels-python/issues) if you think they should stay.

- `frequenz.channels.experimental.NopReceiver` and `frequenz.channels.experimental.WithPrevious` are deprecated. Import them from `frequenz.channels` instead; they are the same objects, so only the import changes. The old names will be removed in v2.0.0.

- The deprecation warning of `frequenz.channels.experimental.OptionalReceiver` now points at `frequenz.channels.NopReceiver`. Use the receiver itself, or a `NopReceiver` when there is none.

- `frequenz.channels.timer.Timer` was renamed to `MonotonicTimer`, to make clear it uses the event loop's monotonic clock and to free the name `Timer` for a wall clock timer in a later version. `Timer` still works as a deprecated alias and will be removed in v2.0.0. The change is mechanical: replace `Timer` with `MonotonicTimer` in imports and uses.

- The deprecation warning of `Anycast` now points at a replacement for its only known use, making senders wait when the channel is full, with a single receiver: a `BroadcastChannel` created with `block_on_full=True`. It gives each message to every receiver instead of one of them, each receiver has its own buffer of `limit` messages (50 by default instead of 10), and it closes itself when all its senders are closed. For other uses, copy `Anycast`'s code into your project, or open an issue if you think it should stay in this library. `Anycast` will be removed in v2.0.0.

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

- `NopReceiver` and `WithPrevious` are now stable, and available from `frequenz.channels`.

- `BroadcastChannel` can now make senders wait instead of dropping messages. With `block_on_full=True`, when a receiver's buffer is full, `send()` waits until every receiver that blocks senders has room, and then gives the message to all receivers at once. A `send()` that is cancelled while waiting, for example by `asyncio.timeout()`, gives the message to no receiver. Close receivers you don't need: one that is never read stops all senders once its buffer is full.

- `BroadcastSender.subscribe()` takes a new keyword-only `block_on_full` argument. By default, it uses the channel's setting, so a receiver that can lose messages can pass `block_on_full=False` and never make senders wait.

- `BroadcastSender.send()` takes a new keyword-only `block_on_full` argument too, for the receivers that use the channel's setting: with `True` the send waits for them, with `False` it never waits and they drop their oldest message. Receivers created with an explicit `block_on_full` keep it. If one created with `block_on_full=True` is full, `send(block_on_full=False)` raises a `SenderWouldBlockError` and no receiver gets the message.

- `TransientSenderError` is a new `SenderError` base class for errors after which the sender and its channel can still be used, like `SenderWouldBlockError`. Catch it before `SenderError` to tell them apart from errors that mean the sender can't be used anymore.

- `CHANNEL_DEFAULT` is a new marker for arguments that take their value from the channel, like `block_on_full` in `subscribe()` and `send()`. It is a PEP 661 sentinel: mypy checks it since version 2.4, older versions accept any value for those arguments.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->

- `BroadcastChannel()` no longer emits the deprecation warning of `Broadcast`, which it uses internally. You were getting a warning about a class you never used.

- `OneshotReceiver.close()` no longer raises `NotImplementedError`. It now works like in the other receivers: a message sent before closing can still be received, and after that receiving raises `ReceiverStoppedError`. The sender can still send, but its message is discarded.

- Creating a broadcast receiver with a `limit` of 0 now raises a `ValueError`, from `BroadcastChannel()`, `BroadcastSender.subscribe()` and `Broadcast.new_receiver()`. Before, the first message sent to it raised an `IndexError`, after other receivers might have got the message already.

- Docstrings now use absolute cross-references to public paths instead of relative ones. Relative cross-references are expanded from the module where an object is defined since mkdocstrings-python 2.0.9, which broke some links, and projects rendering docstrings inherited from this library needed `relative_crossrefs: true` for them to work at all. See [frequenz-repo-config-python#655](https://github.com/frequenz-floss/frequenz-repo-config-python/issues/655) for details.
