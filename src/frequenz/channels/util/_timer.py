# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""A timer receiver that ticks every `interval`.

Note:
    This module always use `int`s to represent time.  The time is always in
    microseconds, so the timer resolution is 1 microsecond.

    This is to avoid floating point errors when performing calculations with
    time, which can lead to very hard to reproduce, and debug, issues.
"""

from __future__ import annotations

import abc
import asyncio
from datetime import timedelta

from .._base_classes import Receiver
from .._exceptions import ReceiverStoppedError


def _to_microseconds(time: float | timedelta) -> int:
    """Convert a time or a timedelta to microseconds.

    Args:
        time: The time to convert. If it is a `float`, it is assumed to be in
            seconds.

    Returns:
        The time in microseconds.
    """
    if isinstance(time, timedelta):
        time = time.total_seconds()
    return round(time * 1_000_000)


class MissedTickPolicy(abc.ABC):
    """A policy to handle timer missed ticks.

    This is only relevant if the timer is not ready to trigger when it should
    (an interval passed) which can happen if the event loop is busy processing
    other tasks.
    """

    @abc.abstractmethod
    def calculate_next_tick_time(
        self, *, interval: int, scheduled_tick_time: int, now: int
    ) -> int:
        """Calculate the next tick time according to `missed_tick_policy`.

        This method is called by `ready()` after it has determined that the
        timer has triggered.  It will check if the timer has missed any ticks
        and handle them according to `missed_tick_policy`.

        Args:
            interval: The interval between ticks (in microseconds).
            scheduled_tick_time: The time the current tick was scheduled to
                trigger (in microseconds).
            now: The current loop time (in microseconds).

        Returns:
            The next tick time (in microseconds) according to
                `missed_tick_policy`.
        """
        return 0  # dummy value to avoid darglint warnings


class TriggerAllMissed(MissedTickPolicy):
    """A policy that triggers all the missed ticks immediately until it catches up.

    Example:
        Assume a timer with interval 1 second, the tick `T0` happens exactly
        at time 0, the second tick, `T1`, happens at time 1.2 (0.2 seconds
        late), so it trigges immediately.  The third tick, `T2`, happens at
        time 2.3 (0.3 seconds late), so it also triggers immediately.  The
        fourth tick, `T3`, happens at time 4.3 (1.3 seconds late), so it also
        triggers immediately as well as the fifth tick, `T4`, which was also
        already delayed (by 0.3 seconds), so it catches up.  The sixth tick,
        `T5`, happens at 5.1 (0.1 seconds late), so it triggers immediately
        again. The seventh tick, `T6`, happens at 6.0, right on time.

        ```
        0         1         2         3         4  o      5         6
        o---------|-o-------|--o------|---------|--o------|o--------o-----> time
        T0          T1         T2                  T3      T5       T6
                                                   T4
        ```
    """

    def calculate_next_tick_time(
        self, *, now: int, scheduled_tick_time: int, interval: int
    ) -> int:
        """Calculate the next tick time.

        This method always returns `scheduled_tick_time + interval`, as all
        ticks need to produce a trigger event.

        Args:
            now: The current loop time (in microseconds).
            scheduled_tick_time: The time the current tick was scheduled to
                trigger (in microseconds).
            interval: The interval between ticks (in microseconds).

        Returns:
            The next tick time (in microseconds).
        """
        return scheduled_tick_time + interval


class SkipMissedAndResync(MissedTickPolicy):
    """A policy that drops all the missed ticks, triggers immediately and resyncs.

    If ticks are missed, the timer will trigger immediately returing the drift
    and it will schedule to trigger again on the next multiple of `interval`,
    effectively skipping any missed ticks, but resyncing with the original start
    time.

    Example:
        Assume a timer with interval 1 second, the tick `T0` happens exactly
        at time 0, the second tick, `T1`, happens at time 1.2 (0.2 seconds
        late), so it trigges immediately.  The third tick, `T2`, happens at
        time 2.3 (0.3 seconds late), so it also triggers immediately.  The
        fourth tick, `T3`, happens at time 4.3 (1.3 seconds late), so it also
        triggers immediately but the fifth tick, `T4`, which was also
        already delayed (by 0.3 seconds) is skipped.  The sixth tick,
        `T5`, happens at 5.1 (0.1 seconds late), so it triggers immediately
        again. The seventh tick, `T6`, happens at 6.0, right on time.

        ```
        0         1         2         3         4  o      5         6
        o---------|-o-------|--o------|---------|--o------|o--------o-----> time
        T0          T1         T2                  T3      T5       T6
        ```
    """

    def calculate_next_tick_time(
        self, *, now: int, scheduled_tick_time: int, interval: int
    ) -> int:
        """Calculate the next tick time.

        Calculate the next multiple of `interval` after `scheduled_tick_time`.

        Args:
            now: The current loop time (in microseconds).
            scheduled_tick_time: The time the current tick was scheduled to
                trigger (in microseconds).
            interval: The interval between ticks (in microseconds).

        Returns:
            The next tick time (in microseconds).
        """
        # We need to resync (align) the next tick time to the current time
        drift = now - scheduled_tick_time
        delta_to_next_tick = interval - (drift % interval)
        return now + delta_to_next_tick


class SkipMissedAndDrift(MissedTickPolicy):
    """A policy that drops all the missed ticks, triggers immediately and resets.

    This will behave effectively as if the timer was `reset()` at the time it
    had triggered last, so the start time will change (and the drift will be
    accumulated each time a tick is delayed, but only the relative drift will
    be returned on each tick).

    The reset happens only if the delay is larger than `delay_tolerance`, so
    it is possible to ignore small delays and not drift in those cases.

    Example:
        Assume a timer with interval 1 second and `delay_tolerance=0.1`, the
        first tick, `T0`, happens exactly at time 0, the second tick, `T1`,
        happens at time 1.2 (0.2 seconds late), so the timer triggers
        immmediately but drifts a bit. The next tick, `T2.2`, happens at 2.3 seconds
        (0.1 seconds late), so it also triggers immediately but it doesn't
        drift because the delay is under the `delay_tolerance`. The next tick,
        `T3.2`, triggers at 4.3 seconds (1.1 seconds late), so it also triggers
        immediately but the timer drifts by 1.1 seconds and the tick `T4.2` is
        skipped (not triggered). The next tick, `T5.3`, triggers at 5.3 seconds
        so is right on time (no drift) and the same happens for tick `T6.3`,
        which triggers at 6.3 seconds.

        ```
        0         1         2         3         4         5         6
        o---------|-o-------|--o------|---------|--o------|--o------|--o--> time
        T0          T1         T2.2                T3.2      T5.3      T6.3
        ```
    """

    def __init__(self, *, delay_tolerance: timedelta = timedelta(0)):
        """
        Create an instance.

        See the class documenation for more details.

        Args:
            delay_tolerance: The maximum delay that is tolerated before
                starting to drift.  If a tick is delayed less than this, then
                it is not considered a missed tick and the timer doesn't
                accumulate this drift.

        Raises:
            ValueError: If `delay_tolerance` is negative.
        """
        self._tolerance: int = _to_microseconds(delay_tolerance)
        """The maximum allowed delay before starting to drift."""

        if self._tolerance < 0:
            raise ValueError("delay_tolerance must be positive")

    @property
    def delay_tolerance(self) -> timedelta:
        """Return the maximum delay that is tolerated before starting to drift.

        Returns:
            The maximum delay that is tolerated before starting to drift.
        """
        return timedelta(microseconds=self._tolerance)

    def calculate_next_tick_time(
        self, *, now: int, scheduled_tick_time: int, interval: int
    ) -> int:
        """Calculate the next tick time.

        If the drift is larger than `delay_tolerance`, then it returns `now +
        interval` (so the timer drifts), otherwise it returns
        `scheduled_tick_time + interval` (we consider the delay too small and
        avoid small drifts).

        Args:
            now: The current loop time (in microseconds).
            scheduled_tick_time: The time the current tick was scheduled to
                trigger (in microseconds).
            interval: The interval between ticks (in microseconds).

        Returns:
            The next tick time (in microseconds).
        """
        drift = now - scheduled_tick_time
        if drift > self._tolerance:
            return now + interval
        return scheduled_tick_time + interval


class Timer(Receiver[timedelta]):
    """A timer receiver that triggers every `interval` time.

    The timer as microseconds resolution, so the `interval` must be at least
    1 microsecond.

    The message it produces is a `timedelta` containing the drift of the timer,
    i.e. the difference between when the timer should have triggered and the time
    when it actually triggered.

    This drift will likely never be `0`, because if there is a task that is
    running when it should trigger, the timer will be delayed. In this case the
    drift will be positive. A negative drift should be technically impossible,
    as the timer uses `asyncio`s loop monotonic clock.

    If the timer is delayed too much, then the timer will behave according to
    the `missed_tick_policy`. Missing ticks might or might not trigger
    a message and the drift could be accumulated or not depending on the
    chosen policy.

    The timer accepts an optional `loop`, which will be used to track the time.
    If `loop` is `None`, then the running loop will be used (if there is no
    running loop most calls will raise a `RuntimeError`).

    Starting the timer can be delayed if necessary by using `auto_start=False`
    (for example until we have a running loop). A call to `reset()`, `ready()`,
    `receive()` or the async iterator interface to await for a new message will
    start the timer.

    For the most common cases, a specialized constructor is provided:

    * [`periodic()`][frequenz.channels.util.Timer.periodic]
    * [`timeout()`][frequenz.channels.util.Timer.timeout]

    Example: Periodic timer example
        ```python
        async for drift in Timer.periodic(timedelta(seconds=1.0)):
            print(f"The timer has triggered {drift=}")
        ```

        But you can also use [`Select`][frequenz.channels.util.Select] to combine it
        with other receivers, and even start it (semi) manually:

        ```python
        import logging
        from frequenz.channels.util import Select
        from frequenz.channels import Broadcast

        timer = Timer.timeout(timedelta(seconds=1.0), auto_start=False)
        chan = Broadcast[int]("input-chan")
        receiver1 = chan.new_receiver()

        timer = Timer.timeout(timedelta(seconds=1.0), auto_start=False)
        # Do some other initialization, the timer will start automatically if
        # a message is awaited (or manually via `reset()`).
        select = Select(bat_1=receiver1, timer=timer)
        while await select.ready():
            if msg := select.bat_1:
                if val := msg.inner:
                    battery_soc = val
                else:
                    logging.warning("battery channel closed")
            elif drift := select.timer:
                # Print some regular battery data
                print(f"Battery is charged at {battery_soc}%")
        ```

    Example: Timeout example
        ```python
        import logging
        from frequenz.channels.util import Select
        from frequenz.channels import Broadcast

        def process_data(data: int):
            logging.info("Processing data: %d", data)

        def do_heavy_processing(data: int):
            logging.info("Heavy processing data: %d", data)

        timer = Timer.timeout(timedelta(seconds=1.0), auto_start=False)
        chan1 = Broadcast[int]("input-chan-1")
        chan2 = Broadcast[int]("input-chan-2")
        receiver1 = chan1.new_receiver()
        receiver2 = chan2.new_receiver()
        select = Select(bat_1=receiver1, heavy_process=receiver2, timeout=timer)
        while await select.ready():
            if msg := select.bat_1:
                if val := msg.inner:
                    process_data(val)
                    timer.reset()
                else:
                    logging.warning("battery channel closed")
            if msg := select.heavy_process:
                if val := msg.inner:
                    do_heavy_processing(val)
                else:
                    logging.warning("processing channel closed")
            elif drift := select.timeout:
                logging.warning("No data received in time")
        ```

        In this case `do_heavy_processing` might take 2 seconds, and we don't
        want our timeout timer to trigger for the missed ticks, and want the
        next tick to be relative to the time timer was last triggered.
    """

    def __init__(
        self,
        interval: timedelta,
        missed_tick_policy: MissedTickPolicy,
        /,
        *,
        auto_start: bool = True,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        """Create an instance.

        See the class documentation for details.

        Args:
            interval: The time between timer ticks. Must be at least
                1 microsecond.
            missed_tick_policy: The policy of the timer when it misses
                a tick. See the documentation of `MissedTickPolicy` for
                details.
            auto_start: Whether the timer should be started when the
                instance is created. This can only be `True` if there is
                already a running loop or an explicit `loop` that is running
                was passed.
            loop: The event loop to use to track time. If `None`,
                `asyncio.get_running_loop()` will be used.

        Raises:
            RuntimeError: if it was called without a loop and there is no
                running loop.
            ValueError: if `interval` is not positive or is smaller than 1
                microsecond.
        """
        self._interval: int = _to_microseconds(interval)
        """The time to between timer ticks."""

        self._missed_tick_policy: MissedTickPolicy = missed_tick_policy
        """The policy of the timer when it misses a tick.

        See the documentation of `MissedTickPolicy` for details.
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

        self._next_tick_time: int | None = None
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

        if self._interval <= 0:
            raise ValueError(
                "The `interval` must be positive and at least 1 microsecond, "
                f"not {interval} ({self._interval} microseconds)"
            )

        if auto_start:
            self.reset()

    @classmethod
    def timeout(
        cls,
        delay: timedelta,
        /,
        *,
        auto_start: bool = True,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> Timer:
        """Create a timer useful for tracking timeouts.

        This is basically a shortcut to create a timer with
        `SkipMissedAndDrift(delay_tolerance=timedelta(0))` as the missed tick policy.

        See the class documentation for details.

        Args:
            delay: The time until the timer ticks. Must be at least
                1 microsecond.
            auto_start: Whether the timer should be started when the
                instance is created. This can only be `True` if there is
                already a running loop or an explicit `loop` that is running
                was passed.
            loop: The event loop to use to track time. If `None`,
                `asyncio.get_running_loop()` will be used.

        Returns:
            The timer instance.

        Raises:
            RuntimeError: if it was called without a loop and there is no
                running loop.
            ValueError: if `interval` is not positive or is smaller than 1
                microsecond.
        """
        return Timer(
            delay,
            SkipMissedAndDrift(delay_tolerance=timedelta(0)),
            auto_start=auto_start,
            loop=loop,
        )

    @classmethod
    def periodic(
        cls,
        period: timedelta,
        /,
        *,
        skip_missed_ticks: bool = False,
        auto_start: bool = True,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> Timer:
        """Create a periodic timer.

        This is basically a shortcut to create a timer with either
        `TriggerAllMissed()` or `SkipMissedAndResync()` as the missed tick policy
        (depending on `skip_missed_ticks`).

        See the class documentation for details.

        Args:
            period: The time between timer ticks. Must be at least
                1 microsecond.
            skip_missed_ticks: Whether to skip missed ticks or trigger them
                all until it catches up.
            auto_start: Whether the timer should be started when the
                instance is created. This can only be `True` if there is
                already a running loop or an explicit `loop` that is running
                was passed.
            loop: The event loop to use to track time. If `None`,
                `asyncio.get_running_loop()` will be used.

        Returns:
            The timer instance.

        Raises:
            RuntimeError: if it was called without a loop and there is no
                running loop.
            ValueError: if `interval` is not positive or is smaller than 1
                microsecond.
        """
        missed_tick_policy = (
            SkipMissedAndResync() if skip_missed_ticks else TriggerAllMissed()
        )
        return Timer(
            period,
            missed_tick_policy,
            auto_start=auto_start,
            loop=loop,
        )

    @property
    def interval(self) -> timedelta:
        """The interval between timer ticks.

        Returns:
            The interval between timer ticks.
        """
        return timedelta(microseconds=self._interval)

    @property
    def missed_tick_policy(self) -> MissedTickPolicy:
        """The policy of the timer when it misses a tick.

        Returns:
            The policy of the timer when it misses a tick.
        """
        return self._missed_tick_policy

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
        self._next_tick_time = self._now() + self._interval
        self._current_drift = None

    def stop(self) -> None:
        """Stop the timer.

        Once `stop` has been called, all subsequent calls to `ready()` will
        immediately return False and calls to `consume()` / `receive()` or any
        use of the async iterator interface will raise
        a `ReceiverStoppedError`.

        You can restart the timer with `reset()`.
        """
        self._stopped = True
        # We need to make sure it's not None, otherwise `ready()` will start it
        self._next_tick_time = self._now()

    async def ready(self) -> bool:
        """Wait until the timer `interval` passed.

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

        now = self._now()
        time_to_next_tick = self._next_tick_time - now
        # If we didn't reach the tick yet, sleep until we do.
        if time_to_next_tick > 0:
            await asyncio.sleep(time_to_next_tick / 1_000_000)
            now = self._now()

        # If a stop was explicitly requested during the sleep, we bail out.
        if self._stopped:
            return False

        self._current_drift = timedelta(microseconds=now - self._next_tick_time)
        self._next_tick_time = self._missed_tick_policy.calculate_next_tick_time(
            now=now,
            scheduled_tick_time=self._next_tick_time,
            interval=self._interval,
        )

        return True

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

    def _now(self) -> int:
        """Return the current monotonic clock time in microseconds.

        Returns:
            The current monotonic clock time in microseconds.
        """
        return _to_microseconds(self._loop.time())
