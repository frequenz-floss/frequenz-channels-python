# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

- `frequenz-core >= 1.6.0, < 2` is now a runtime dependency. It provides the utilities this project uses to deprecate symbols following the Frequenz deprecations guide.

- The minimum `typing-extensions` version is now 4.13.0, which `frequenz-core` requires.

- `frequenz.channels.experimental.GroupingLatestValueCache` and its type variables `DefaultT`, `HashableT` and `ValueT_co`, and `frequenz.channels.experimental.RelaySender` are deprecated and will be removed in v2.0.0. There is no replacement in this library: copy their code into your project if you need them, or [open an issue](https://github.com/frequenz-floss/frequenz-channels-python/issues) if you think they should stay.

- `frequenz.channels.experimental.NopReceiver` and `frequenz.channels.experimental.WithPrevious` are deprecated. Import them from `frequenz.channels` instead; they are the same objects, so only the import changes. The old names will be removed in v2.0.0.

- The deprecation warning of `frequenz.channels.experimental.OptionalReceiver` now points at `frequenz.channels.NopReceiver`. Use the receiver itself, or a `NopReceiver` when there is none.

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

- `NopReceiver` and `WithPrevious` are now stable, and available from `frequenz.channels`.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->

- `BroadcastChannel()` no longer emits the deprecation warning of `Broadcast`, which it uses internally. You were getting a warning about a class you never used.

- Docstrings now use absolute cross-references to public paths instead of relative ones. Relative cross-references are expanded from the module where an object is defined since mkdocstrings-python 2.0.9, which broke some links, and projects rendering docstrings inherited from this library needed `relative_crossrefs: true` for them to work at all. See [frequenz-repo-config-python#655](https://github.com/frequenz-floss/frequenz-repo-config-python/issues/655) for details.
