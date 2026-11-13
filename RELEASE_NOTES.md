# Frequenz channels Release Notes

## Summary

This will probably be the last minor release of v1. It deprecates everything that will be removed in v2.0.0.

## Upgrading

- `frequenz-core >= 1.6.0, < 2` is now a runtime dependency. It provides the utilities this project uses to deprecate symbols following the Frequenz deprecations guide.

- The minimum `typing-extensions` version is now 4.16.0. `frequenz-core` requires 4.13.0, and the new `buffer_size` argument needs the `sentinel` type added in 4.16.0.

- `watchfiles` 1.2 and 1.3 are now allowed (`watchfiles >= 0.15.0, < 1.4.0`).

- `frequenz.channels.Anycast`, deprecated since v1.12.0, will be removed in a future version, not necessarily the next major one. Its deprecation warning now recommends copying its code into your project if you need it, or [opening an issue](https://github.com/frequenz-floss/frequenz-channels-python/issues) if you think it should stay in the library.

- `frequenz.channels.Broadcast`, deprecated since v1.12.0, now warns `frequenz.channels.Broadcast is deprecated. Use frequenz.channels.BroadcastChannel instead.`, instead of `Please use BroadcastChannel instead.`.

- `Broadcast.close()` and `Anycast.close()`, deprecated since v1.8.0, will be removed in v2.0.0. Use `aclose()` instead. Their deprecation warnings now say so, and name the method and its class, as in `The method close() in frequenz.channels.Broadcast is deprecated and will be removed in v2.0.0. Use aclose() instead.`

- `frequenz.channels.experimental.GroupingLatestValueCache` and its type variables `DefaultT`, `HashableT` and `ValueT_co`, and `frequenz.channels.experimental.RelaySender` are deprecated and will be removed in v2.0.0. There is no replacement in this library: copy their code into your project if you need them, or [open an issue](https://github.com/frequenz-floss/frequenz-channels-python/issues) if you think they should stay.

- `frequenz.channels.experimental.NopReceiver` and `frequenz.channels.experimental.WithPrevious` are deprecated. Import them from `frequenz.channels` instead; they are the same objects, so only the import changes. The old names will be removed in v2.0.0, and their deprecation warnings say so.

- `frequenz.channels.experimental.OptionalReceiver` will be removed in v2.0.0. Its deprecation warning now points at `frequenz.channels.NopReceiver`: use the receiver itself, or a `NopReceiver` when there is none.

- `frequenz.channels.timer.Timer` was renamed to `MonotonicTimer`, to make clear it uses the event loop's monotonic clock and to free the name `Timer` for a wall clock timer in a later version. `Timer` still works as a deprecated alias and will be removed in v2.0.0, as its deprecation warning says. The change is mechanical: replace `Timer` with `MonotonicTimer` in imports and uses.

- The `limit` argument of `BroadcastChannel()` and `BroadcastSender.subscribe()` is deprecated and will be removed in v2.0.0. Use the new `buffer_size` argument instead. It does the same, but its name says what is limited: the number of messages each receiver can hold.

  - `buffer_size` is keyword-only, and passing both `limit` and `buffer_size` raises a `TypeError`.
  - Passing `warn_on_overflow` by position is deprecated, since the `buffer_size` form only accepts it by keyword.
  - v2.0.0 will also make `resend_latest` keyword-only, so pass it by keyword now.
  - `Broadcast` and `Anycast` are not changed.

## New Features

- `NopReceiver` and `WithPrevious` are now stable, and available from `frequenz.channels`.

## Bug Fixes

- `BroadcastChannel()` no longer emits the deprecation warning of `Broadcast`, which it uses internally. You were getting a warning about a class you never used.

- `OneshotReceiver.close()` no longer raises `NotImplementedError`. It now works like in the other receivers: a message sent before closing can still be received, and after that receiving raises `ReceiverStoppedError`. The sender can still send, but its message is discarded.

- Creating a broadcast receiver with a `buffer_size` (or `limit`) of 0 now raises a `ValueError`, from `BroadcastChannel()` and `BroadcastSender.subscribe()`. Before, the first message sent to it raised an `IndexError`, after other receivers might have got the message already.

- Docstrings now use absolute cross-references to public paths instead of relative ones. Relative cross-references are expanded from the module where an object is defined since mkdocstrings-python 2.0.9, which broke some links, and projects rendering docstrings inherited from this library needed `relative_crossrefs: true` for them to work at all. See [frequenz-repo-config-python#655](https://github.com/frequenz-floss/frequenz-repo-config-python/issues/655) for details.
