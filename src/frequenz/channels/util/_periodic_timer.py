# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""A periodic timer receiver that ticks every `interval`."""

from __future__ import annotations

import asyncio
import enum
from datetime import timedelta

from .._base_classes import Receiver
from .._exceptions import ReceiverStoppedError


class MissedTickBehavior(enum.Enum):
    """The behavior of the timer when it misses a tick.

    This is only relevant if the timer is not ready to trigger when it should
    (an interval passed) which can happen if the event loop is busy processing
    other tasks.
    """

    TRIGGER_ALL = enum.auto()
    """Trigger all the missed ticks immediately until it catches up.

    The start time of the timer will not change and the drift will also not be
    accumulated.

    The `delay_tolerance` is ignored in this mode.

    For example, if the timer missed 3 ticks exactly, then the timer will
    trigger 4 times immediately: the first returned drift will be 3 * interval,
    the second will be 2 * interval, the third will be 1 * interval and the
    fourth will be 0 (assuming zero processing time for catching up).
    """

    SKIP_AND_DRIFT = enum.auto()
    """Drop all the missed ticks, trigger immediately and reset.

    This will behave effectively as if the timer was `reset()` at the time it
    had triggered last, so the start time will change (and the drift will be
    accumulated each time a tick is delayed, but only the relative drift will
    be returned on each tick).

    The reset happens only if the delay is larger than `delay_tolerance`.

    For example, if the timer missed 3 ticks exactly, then the first returned
    drift will be 3 * interval, and the second will be 0 if there were no more
    delays.
    """

    SKIP_AND_RESYNC = enum.auto()
    """Drop all the missed ticks, trigger immediately and resync with interval.

    If ticks are missed, the timer will trigger immediately returing the drift
    and it will schedule to trigger again on the next multiple of `interval`.
    The start time of the timer will not change and the drift will also not be
    accumulated.

    The missed ticks are only skipped if the delay is larger than
    `delay_tolerance`.

    For example, if the timer missed 3 ticks exactly, then the first returned
    drift will be 3 * interval but subsequent drifts will be 0 if the timer
    ticks on time.
    """


class PeriodicTimer(Receiver[timedelta]):
    """A periodic timer receiver that triggers every `interval` time.

    The message it produces is a `timedelta` containing the drift of the timer,
    i.e. the difference between when the timer should have triggered and the time
    when it actually triggered.

    This drift will likely never be `0`, because if there is a task that is
    running when it should trigger, the timer will be delayed. In this case the
    drift will be positive. A negative drift should be technically impossible,
    as the timer uses `asyncio`s loop monotonic clock.

    If the timer is delayed too much (see `delay_tolerance`), then the timer
    will behave according to the `missed_tick_behavior`. Missing ticks might
    or might not trigger a message and the drift could be accumulated or not.

    The timer accepts an optional `loop`, which will be used to track the time.
    If `loop` is `None`, then the running loop will be used (if there is no
    running loop most calls will raise a `RuntimeError`).

    Starting the timer can be delayed if necessary by using `auto_start=False`
    (for example until we have a running loop). A call to `reset()`, `ready()`,
    `receive()` or the async iterator interface to await for a new message will
    start the timer.

    Example:
        The most common use case is to just do something periodically:

        ```python
        async for drift in PeriodicTimer(timedelta(seconds=1.0)):
            print(f"The timer has triggered {drift=}")
        ```

        But you can also use [Select][frequenz.channels.util.Select] to combine
        it with other receivers, and even start it (semi) manually:

        ```python
        timer = PeriodicTimer(timedelta(seconds=1.0), auto_start=False)
        # Do some other initialization, the timer will start automatically if
        # a message is awaited (or manually via `reset()`).
        select = Select(bat_1=receiver1, timer=timer)
        while await select.ready():
            if msg := select.bat_1:
                if val := msg.inner:
                    process_data(val)
                else:
                    logging.warn("battery channel closed")
            elif drift := select.timer:
                # Print some regular battery data
                print(f"Battery is charged at {battery.soc}%")
                if stop_logging:
                    timer.stop()
                elif start_logging:
                    timer.reset()
        ```

        For timeouts it might be useful to use `MissedTickBehavior.SKIP_AND_DRIFT`
        and `delay_tolerance=timedelta(0)`, so the timer always gets
        automatically reset:

        ```python
        timer = PeriodicTimer(timedelta(seconds=1.0),
            auto_start=False,
            missed_tick_behavior=MissedTickBehavior.SKIP_AND_DRIFT,
            delay_tolerance=timedelta(0),
        )
        select = Select(bat_1=receiver1, heavy_process=receiver2, timeout=timer)
        while await select.ready():
            if msg := select.bat_1:
                if val := msg.inner:
                    process_data(val)
                    timer.reset()
                else:
                    logging.warn("battery channel closed")
            if msg := select.heavy_process:
                if val := msg.inner:
                    do_heavy_processing(val)
                else:
                    logging.warn("processing channel closed")
            elif drift := select.timeout:
                logging.warn("No data received in time")
        ```

        In this case `do_heavy_processing` might take 2 seconds, and we don't
        want our timeout timer to trigger for the missed ticks, and want the
        next tick to be relative to the time timer was last triggered.
    """

    def __init__(
        self,
        /,
        interval: timedelta,
        *,
        auto_start: bool = True,
        missed_tick_behavior: MissedTickBehavior = MissedTickBehavior.TRIGGER_ALL,
        delay_tolerance: timedelta | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """Create an instance.

        See the class documentation for details.

        Args:
            interval: The time between timer ticks.
            auto_start: Whether the periodic timer should be started when the
                instance is created. This can only be `True` if there is
                already a running loop or an explicit `loop` that is running
                was passed.
            missed_tick_behavior: The behavior of the timer when it misses
                a tick. See the documentation of `MissedTickBehavior` for
                details.
            delay_tolerance: The maximum delay that is tolerated before
                adjusting ticks according to `missed_tick_behavior`.  If
                a tick is delayed less than this, then it is not considered
                a missed tick. By default this is set to 1% of the interval.
                Bear in mind that some `MissedTickBehavior`s ignore this value.
            loop: The event loop to use to track time. If `None`,
                `asyncio.get_running_loop()` will be used.

        Raises:
            RuntimeError: if it was called without a loop and there is no
                running loop.
        """
        self._interval: timedelta = interval
        """The time to between timer ticks."""

        self._missed_tick_behavior: MissedTickBehavior = missed_tick_behavior
        """The behavior of the timer when it misses a tick.

        See the documentation of `MissedTickBehavior` for details.
        """

        self._delay_tolerance: timedelta = (
            (interval / 100) if delay_tolerance is None else delay_tolerance
        )
        """The maximum allowed delay before triggering `missed_tick_behavior`.

        If a tick is delayed less than this, then it is not considered a missed
        tick. Bear in mind that some `MissedTickBehavior`s ignore this value.
        """

        self._loop: asyncio.AbstractEventLoop = (
            loop if loop is not None else asyncio.get_running_loop()
        )
        """The event loop to use to track time."""

        self._stopped: bool = True
        """Whether the timer was requested to stop.

        If this is `False`, then the timer is running.

        If this is `True`, then it is stopped or there is a request to stop it
        or it was not started yet:

        * If `_next_msg_time` is `None`, it means it wasn't started yet (it was
          created with `auto_start=False`).  Any receiving method will start
          it by calling `reset()` in this case.

        * If `_next_msg_time` is not `None`, it means there was a request to
          stop it.  In this case receiving methods will raise
          a `ReceiverClosedError`.
        """

        self._next_tick_time: float | None = None
        """The absolute (monotonic) time when the timer should trigger.

        If this is `None`, it means the timer didn't start yet, but it should
        be started as soon as it is used.
        """

        self._current_drift: timedelta | None = None
        """The difference between `_next_msg_time` and the triggered time.

        This is calculated by `ready()` but is returned by `consume()`. If
        `None` it means `ready()` wasn't called and `consume()` will assert.
        `consume()` will set it back to `None` to tell `ready()` that it needs
        to wait again.
        """

        if auto_start:
            self.reset()

    @property
    def interval(self) -> timedelta:
        """The interval between timer ticks.

        Returns:
            The interval between timer ticks.
        """
        return self._interval

    @property
    def missed_tick_behavior(self) -> MissedTickBehavior:
        """The behavior of the timer when it misses a tick.

        Returns:
            The behavior of the timer when it misses a tick.
        """
        return self._missed_tick_behavior

    @property
    def delay_tolerance(self) -> timedelta:
        """The maximum allowed delay before triggering `missed_tick_behavior`.

        Returns:
            The maximum allowed delay before triggering
                `missed_tick_behavior`.
        """
        return self._delay_tolerance

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """The event loop used by the timer to track time.

        Returns:
            The event loop used by the timer to track time.
        """
        return self._loop

    @property
    def is_running(self) -> bool:
        """Whether the timer is running.

        This will be `False` if the timer was stopped, or not started yet.

        Returns:
            Whether the timer is running.
        """
        return not self._stopped

    def reset(self) -> None:
        """Reset the timer to start timing from now.

        If the timer was stopped, or not started yet, it will be started.

        This can only be called with a running loop, see the class
        documentation for more details.

        Raises:
            RuntimeError: if it was called without a running loop.
        """
        self._stopped = False
        self._next_tick_time = self._loop.time() + self._interval.total_seconds()

    def stop(self) -> None:
        """Stop the timer.

        Once `stop` has been called, all subsequent calls to `ready()` will
        immediately return False and calls to `consume()` / `receive()` or any
        use of the async iterator interface will raise
        a `ReceiverStoppedError`.

        You can restart the timer with `reset()`.
        """
        self._stopped = True
        self._next_tick_time = -1.0

    async def ready(self) -> bool:
        """Wait until the timer interval passed.

        Once a call to `ready()` has finished, the resulting tick information
        must be read with a call to `consume()` (`receive()` or iterated over)
        to tell the timer it should wait for the next interval.

        The timer will remain ready (this method will return immediately)
        until it is consumed.

        Returns:
            Whether the timer was started and it is still running.

        Raises:
            RuntimeError: if it was called without a running loop.
        """
        # If there are messages waiting to be consumed, return immediately.
        if self._current_drift is not None:
            return True

        # If `_next_tick_time` is `None`, it means it was created with
        # `auto_start=False` and should be started.
        if self._next_tick_time is None:
            self.reset()
            assert (
                self._next_tick_time is not None
            ), "This should be assigned by reset()"

        # If a stop was explicitly requested, we bail out.
        if self._stopped:
            return False

        now = self._loop.time()
        time_to_next_tick = self._next_tick_time - now
        # If we didn't reach the tick yet, sleep until we do.
        if time_to_next_tick > 0:
            await asyncio.sleep(time_to_next_tick)
            now = self._loop.time()

        self._current_drift = timedelta(seconds=now - self._next_tick_time)

        # There is no relevant delay or we want to emit all the ticks, we just
        # calculate the next tick time and return.
        if (
            self._current_drift <= self._delay_tolerance
            or self._missed_tick_behavior is MissedTickBehavior.TRIGGER_ALL
        ):
            self._next_tick_time = self._next_tick_time + self._interval.total_seconds()
            return True

        # At this point we have a considerable delay and need to skip ticks

        if self._missed_tick_behavior is MissedTickBehavior.SKIP_AND_DRIFT:
            self.reset()
            return True

        if self._missed_tick_behavior is MissedTickBehavior.SKIP_AND_RESYNC:
            # We need to resync (align) the next tick time to the current time
            total_missed, reminder = divmod(self._current_drift, self._interval)
            delta_to_next_tick = self._interval * (total_missed + 1) - reminder
            self._next_tick_time = now + delta_to_next_tick.total_seconds()
            return True

        assert False, "Unknown MissedTickBehavior"

    def consume(self) -> timedelta:
        """Return the latest drift once `ready()` is complete.

        Once the timer has triggered (`ready()` is done), this method returns the
        difference between when the timer should have triggered and the time when
        it actually triggered. See the class documentation for more details.

        Returns:
            The difference between when the timer should have triggered and the
                time when it actually did.

        Raises:
            ReceiverStoppedError: if the timer was stopped via `stop()`.
        """
        # If it was stopped and there it no pending result, we raise
        # (if there is a pending result, then we still want to return it first)
        if self._stopped and self._current_drift is None:
            raise ReceiverStoppedError(self)

        assert (
            self._current_drift is not None
        ), "calls to `consume()` must be follow a call to `ready()`"
        drift = self._current_drift
        self._current_drift = None
        return drift
