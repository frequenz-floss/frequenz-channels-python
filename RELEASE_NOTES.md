# Frequenz channels Release Notes

## Summary

The `Timer` now can be started with a delay.

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

* `Timer()`, `Timer.timeout()`, `Timer.periodic()` and `Timer.reset()` now take an optional `start_delay` option to make the timer start after some delay.

  This can be useful, for example, if the timer needs to be *aligned* to a particular time. The alternative to this would be to `sleep()` for the time needed to align the timer, but if the `sleep()` call gets delayed because the event loop is busy, then a re-alignment is needed and this could go on for a while. The only way to guarantee a certain alignment (with a reasonable precision) is to delay the timer start.

* The `Broadcast.wait_for_receiver()` method was added to allow waiting for a receiver to be connected to the broadcast channel.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
