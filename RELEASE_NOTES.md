# Frequenz channels Release Notes

## Upgrading

- `LatestValueCache` now closes the receiver when it is stopped.
- Fetching values from stopped `LatestValueCache` instances is now disallowed.

## New Features

- There's a new `Oneshot` channel, which returns a sender and a receiver.  A single message can be sent using the sender, after which it will be closed.  And the receiver will close as soon as the message is received.

- `Sender`s now have an `aclose`, which must be called, when they are no-longer needed.
