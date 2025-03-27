# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

- An optional `tick_at_start` parameter has been added to `Timer`.  When `True`, the timer will trigger immediately after starting, and then wait for the interval before triggering again.
- Add `Receiver.fork` method to create independent clones of the receiver.
    - Useful for scenarios where multiple consumers need to process the same stream of messages. Each forked receiver.
    - Each forked receiver maintains its own independent message queue

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
