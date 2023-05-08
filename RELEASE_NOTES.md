# Frequenz Channels Release Notes

## Summary

This release adds support to pass `None` values via channels and revamps the `Timer` class to support custom policies for handling missed ticks and use the loop monotonic clock.

## Upgrading

* `util.Timer` was replaced by a more generic implementation that allows for customizable policies to handle missed ticks.

  If you were using `Timer` to implement timeouts, these two pices of code should be almost equivalent:

  - Old:

    ```python
    old_timer = Timer(1.0)
    triggered_datetime = old_timer.receive()
    ```

  - New:

    ```python
    new_timer = Timer.timeout(timedelta(seconds=1.0))
    drift = new_timer.receive()
    triggered_datetime = datetime.now(timezone.utc) - drift
    ```

  They are not **exactly** the same because the `triggered_datetime` in the second case will not be exactly when the timer had triggered, but that shouldn't be relevant, the important part is when your code can actually react to the timer trigger and to know how much drift there was to be able to take corrective actions.

  Also the new `Timer` uses the `asyncio` loop monotonic clock and the old one used the wall clock (`datetime.now()`) to track time. This means that when using `async-solipsism` to test, the new `Timer` will always trigger immediately regarless of the state of the wall clock.

  **Note:** Before replacing this code blindly in all uses of `Timer.timeout()`, please consider using the periodic timer constructor `Timer.periodic()` if you need a timer that triggers reliable on a periodic fashion, as the old `Timer` (and `Timer.timeout()`) accumulates drift, which might not be what you want.

## New Features

* `util.Timer` was replaced by a more generic implementation that allows for customizable policies to handle missed ticks.

* Passing `None` values via channels is now supported.

## Bug Fixes

* `util.Select` / `util.Merge` / `util.MergeNamed`: Cancel pending tasks in `__del__` methods only if possible (the loop is not already closed).
