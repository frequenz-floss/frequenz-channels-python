# Frequenz channels Release Notes

## Summary

The `Timer` now can be started with a delay.

## Upgrading

* Internal variable names in the `Anycast` and `Broadcast` implementations are now private.

## New Features

* `Timer()`, `Timer.timeout()`, `Timer.periodic()` and `Timer.reset()` now take an optional `start_delay` option to make the timer start after some delay.

  This can be useful, for example, if the timer needs to be *aligned* to a particular time. The alternative to this would be to `sleep()` for the time needed to align the timer, but if the `sleep()` call gets delayed because the event loop is busy, then a re-alignment is needed and this could go on for a while. The only way to guarantee a certain alignment (with a reasonable precision) is to delay the timer start.

* `Broadcast.resend_latest` is now a public attribute, allowing it to be changed after the channel is created.

* The arm64 architecture is now officially supported.

* The documentation was improved to:

  - Show signatures with types.
  - Show the inherited members.
  - Documentation for pre-releases are now published.
  - Show the full tag name as the documentation version.
  - All development branches now have their documentation published (there is no `next` version anymore).
  - Fix the order of the documentation versions.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
