# Frequenz channels Release Notes

## Summary

This release fixes timers ignoring the cancellation of a task waiting on them, which could make stopping a service hang for a whole timer interval.

## Bug Fixes

- Cancelling a task that waits on a `MonotonicTimer`, directly or through `select()`, is no longer ignored when it arrives right after the timer was reset or ticked. Before, the task could keep waiting until the next tick, so stopping a service could hang for a whole timer interval.
