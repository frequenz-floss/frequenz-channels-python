# Frequenz channels Release Notes

## Upgrading

- The old `Broadcast` class is deprecated in favour of the new auto-closing `BroadcastChannel`.

- The `Anycast` class is deprecated, because of the lack of use-cases and the maintenance cost.

## New Features

- There's a new `BroadcastChannel`, which returns a broadcast sender and a broadcast receiver.  The channel is auto-closing, meaning when all the senders or all the receivers are closed, the channel is closed.
