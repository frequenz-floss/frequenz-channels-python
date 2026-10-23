# Frequenz channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

<!-- Here goes notes on how to upgrade from previous versions, including deprecations and what they should be replaced with -->

## New Features

<!-- Here goes the main new features and examples or instructions on how to use them -->

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->

- Docstrings now use absolute cross-references to public paths instead of relative ones. Relative cross-references are expanded from the module where an object is defined since mkdocstrings-python 2.0.9, which broke some links, and projects rendering docstrings inherited from this library needed `relative_crossrefs: true` for them to work at all. See [frequenz-repo-config-python#655](https://github.com/frequenz-floss/frequenz-repo-config-python/issues/655) for details.
