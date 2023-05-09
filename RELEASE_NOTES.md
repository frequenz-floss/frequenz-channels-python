# Frequenz Channels Release Notes

## Summary

This release adds support to pass `None` values via channels and revamps the `Timer` class to support custom policies for handling missed ticks and use the loop monotonic clock.  There is also a fix for the `FileWatcher` which includes a change in behavior when reporting changes for deleted files.

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

  Also the new `Timer` uses the `asyncio` loop monotonic clock and the old one used the wall clock (`datetime.now()`) to track time. This means that when using `async-solipsism` to test, the new `Timer` will always trigger immediately regarless of the state of the wall clock.  This also means that we don't need to mock the wall clock with `time-machine` either now.

  With the previous timer one needed to create a separate task to run the timer, because otherwise it would block as it loops until the wall clock was at a specific time. Now the code will run like this:

  ```python
  timer = Timer.timeout(timedelta(seconds=1.0))
  asyncio.sleep(0.5)  # Advances the loop monotonic clock by 0.5 seconds immediately
  await drift = timer.receive()  # Advances the clock by 0.5 immediately too
  assert drift == approx(timedelta(0))  # Because it could trigger exactly at the tick time

  # Simulates a delay in the timer trigger time
  asyncio.sleep(1.5)  # Advances the loop monotonic clock by 1.5 seconds immediately
  await drift = timer.receive()  # The timer should have triggerd 0.5 seconds ago, so it doesn't even sleep
  assert drift == approx(timedelta(seconds=0.5))  # Now we should observe a drift of 0.5 seconds
  ```

  **Note:** Before replacing this code blindly in all uses of `Timer.timeout()`, please consider using the periodic timer constructor `Timer.periodic()` if you need a timer that triggers reliable on a periodic fashion, as the old `Timer` (and `Timer.timeout()`) accumulates drift, which might not be what you want.

* `FileWatcher` now will emit events even if the file doesn't exist anymore.

  Because the underlying library has a considerable delay in triggering filesystem events, it can happen that, for example, a `CREATE` event is received but at the time of receiving the file doesn't exist anymore (because if was removed just after creation and before the event was triggered).

  Before the `FileWatcher` will only emit events when the file exists, but this doesn't work for `DELETE` events (clearly). Given the nature of this mechanism can lead to races easily, it is better to leave it to the user to decide when these situations happen and just report all events.

  Therefore, you should now check a file receiving an event really exist before trying to operate on it.

* `FileWatcher` reports the type of event observed in addition to the file path.

  Previously, only the file path was reported. With this update, users can now determine if a file change is a creation, modification, or deletion.
  Note that this change may require updates to your existing code that relies on `FileWatcher` as the new interface returns a `FileWatcher.Event` instead of just the file path.

## New Features

* `util.Timer` was replaced by a more generic implementation that allows for customizable policies to handle missed ticks.

* Passing `None` values via channels is now supported.

* `FileWatcher.Event` was added to notify events when a file is created, modified, or deleted.

## Bug Fixes

* `util.Select` / `util.Merge` / `util.MergeNamed`: Cancel pending tasks in `__del__` methods only if possible (the loop is not already closed).

* `FileWatcher` will now report `DELETE` events correctly.

  Due to a bug, before this release `DELETE` events were only reported if the file was re-created before the event was triggered.
