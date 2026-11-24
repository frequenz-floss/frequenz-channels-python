# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

## Bug Fixes

- Cancelling a task that waits on a `MonotonicTimer` (or the deprecated `Timer`), directly or through `select()`, is no longer ignored when it arrives right after the timer was reset or ticked. Before, the task could keep waiting until the next tick, so stopping a service could hang for a whole timer interval.
