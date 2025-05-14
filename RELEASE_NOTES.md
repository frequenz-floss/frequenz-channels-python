# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

- An experimental `NopReceiver` implementation has been added, which can be used as a place-holder receiver that never receives a message.

- The experimental `OptionalReceiver` has been deprecated.  It will be removed with the next major release.  It can be replaced with a `NopReceiver` as follows:

  ```python
  opt_recv: Receiver[T] | None
  recv: Receiver[T] = NopReceiver[T]() if opt_recv is None else opt_recv
  ```

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
