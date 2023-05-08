# Frequenz Channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

* `util.Timer` was replaced by a more generic implementation that allows for customizable policies to handle missed ticks.

  These two pices of code should be almost equivalent:

  - Old:

    ```python
    old_timer = Timer(1.0)
    triggered_datetime = old_timer.receive()
    ```

  - New:

    ```python
    new_timer = Timer(timedelta(seconds=1.0), SkipMissedAndDrift())
    drift = new_timer.receive()
    triggered_datetime = datetime.now(timezone.utc) - drift
    ```

  They are not **exactly** the same because the `triggered_datetime` in the second case will not be exactly when the timer had triggered, but that shouldn't be relevant, the important part is when your code can actually react to the timer trigger and to know how much drift there was to be able to take corrective actions.

  Also the new `Timer` uses the `asyncio` loop monotonic clock and the old one used the wall clock (`datetime.now()`) to track time. This means that when using `async-solipsism` to test, the new `Timer` will always trigger immediately regarless of the state of the wall clock.

  **Note:** Before replacing this code blindly in all uses of `Timer`, please consider using the default `TriggerAllMissed()` or `SkipMissedAndResync()`, as the old `Timer` accumulated drift, which might not be what you want unless you are using it to implement timeouts.

## New Features

* `util.Timer` was replaced by a more generic implementation that allows for customizable policies to handle missed ticks.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
