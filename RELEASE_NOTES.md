# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

- An optional `tick_at_start` parameter has been added to `Timer`.  When `True`, the timer will trigger immediately after starting, and then wait for the interval before triggering again.

## Bug Fixes

- Fix unterminated code block in a documentation example for `WithPrevious`.
