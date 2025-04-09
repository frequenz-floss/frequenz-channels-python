# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

- Some minimal dependencies have been bumped, so you might need to adjust your dependencies accordingly.
- `Broadcast` and `Anycast` channels method `close()` was renamed to `aclose()` to follow Python's convention. With this change now channels can be used with the [`aclosing()`](https://docs.python.org/3/library/contextlib.html#contextlib.aclosing) context manager for example.

   The name `close()` is still available for backwards compatibility, but it will be removed in the next major release, so it is recommended to switch to `aclose()`.

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
