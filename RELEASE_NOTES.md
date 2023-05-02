# Frequenz Channels Release Notes

## Summary

<!-- Here goes a general summary of what this release is about -->

## Upgrading

* `util.Timer` was removed and replaced by `util.PeriodicTimer`.

  These two pices of code should be almost equivalent:

  - Old:

    ```python
    old_timer = Timer(1.0)
    triggered_datetime = old_timer.receive()
    ```

  - New:

    ```python
    new_timer = PeriodicTimer(timedelta(seconds=1.0),
        missed_ticks_behaviour=MissedTickBehavior.SKIP_AND_DRIFT,
    )
    drift = new_timer.receive()
    triggered_datetime = datetime.now(timezone.utc) - drift
    ```

  They are not **exactly** the same because the `triggered_datetime` in the second case will not be exactly when the timer had triggered, but that shouldn't be relevant, the important part is when your code can actually react to the timer trigger and to know how much drift there was to be able to take corrective actions.

  Also `PeriodicTimer` uses the `asyncio` loop monotonic clock and `Timer` used the wall clock (`datetime.now()`) to track time. This means that when using `async-solipsism` to test, `PeriodicTimer` will always trigger immediately regarless of the state of the wall clock.

  **Note:** Before replacing this code blindly in all uses of `Timer`, please consider using the default `MissedTickBehavior.TRIGGER_ALL` or `MissedTickBehavior.SKIP_AND_RESYNC`, as the old `Timer` accumulated drift, which might not be what you want unless you are using it to implement timeouts.

## New Features

* A new receiver `util.PeriodicTimer` was added. This implements a periodic timer using `asyncio`'s monotonic clock and adds customizable behaviour on missed ticks.

## Bug Fixes

<!-- Here goes notable bug fixes that are worth a special mention or explanation -->
