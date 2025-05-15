# Frequenz channels Release Notes

## New Features

- An experimental `NopReceiver` implementation has been added, which can be used as a place-holder receiver that never receives a message.

- The experimental `OptionalReceiver` has been deprecated.  It will be removed with the next major release.  It can be replaced with a `NopReceiver` as follows:

  ```python
  opt_recv: Receiver[T] | None
  recv: Receiver[T] = NopReceiver[T]() if opt_recv is None else opt_recv
  ```
