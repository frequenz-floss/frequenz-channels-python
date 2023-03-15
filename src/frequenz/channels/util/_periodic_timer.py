# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A timer receiver that returns the timestamp every `interval`."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from .._base_classes import Receiver
from .._exceptions import ReceiverStoppedError


class PeriodicTimer(Receiver[timedelta]):
    """A periodic timer receiver that fires every `interval` time.

    The message it produces is a `timedelta` containing the drift of the timer,
    i.e. the difference between when the timer should have fired and the time
    when it actually fired. Note that the drift will not be accumulated by the
    timer, which will be automatically adjusted so it only fires (or tries to)
    in multiples of the `interval`.

    This will not always be `0`, because if there is a task that is running when it
    should fire, the timer will be delayed. In this case the drift will be
    positive. A negative drift should be technically impossible, as the timer
    uses `asyncio`s loop monotonic clock.

    Because of this, the timer can only be started once an event loop is
    running. Starting the timer can be delayed if necessary (for example until
    we have a running loop). A call to `reset()`, `ready()`, `receive()` or the
    async iterator interface to await for a new message will start the timer.

    Example:
        The most common use case is to just do something periodically:

        ```python
        async for drift in PeriodicTimer(30.0):
            print(f"The timer has fired {drift=}")
        ```

        But you can also use [Select][frequenz.channels.util.Select] to combine
        it with other receivers, and even start it (semi) manually:

        ```python
        timer = PeriodicTimer(30.0, auto_start=False)
        # Do some other initialization, the timer will start automatically if
        # a message is awaited (or manually via `reset()`).
        select = Select(bat_1=receiver1, timer=timer)
        while await select.ready():
            if msg := select.bat_1:
                if val := msg.inner:
                    process_data(val)
                else:
                    logging.warn("battery channel closed")
            if drift := select.timer:
                # Print some regular battery data
                print(f"Battery is charged at {battery.soc}%")
                if stop_logging:
                    timer.stop()
                elif start_logging:
                    timer.reset()
        ```
    """

    def __init__(self, /, interval: timedelta, *, auto_start: bool = True) -> None:
        """Create an instance.

        See the class documentation for details.

        Args:
            interval: The time between timer fires (producing a message).
            auto_start: Whether the periodic timer should be started when the
                instance is created. This can only be true if there is already
                a running loop.

        Raises:
            RuntimeError: if it was called without a running loop.
        """
        self._interval: float = interval.total_seconds()
        """The interval to wait until the next fire."""

        self._stopped: bool = False
        """Whether the timer was requested to stop.

        If there is no request to stop, any receiving method will start it by
        calling `reset()`. If this is True, receiving methods will raise
        a `ReceiverStoppedError`.

        When the timer is not `auto_start`ed, this will be `False`, but
        `_next_msg_time` will be `None`, indicating receiving methods that they
        should start the timer.
        """

        self._next_msg_time: float | None = None
        """The absolute (monotonic) time when the timer should fire.

        If this is None, it means the timer either didn't started (if
        `_stopped` is `False`) or was explicitly stopped (if `_stopped` is
        `True`).
        """

        self._current_drift: timedelta | None = None
        """The difference between `_next_msg_time` and the actual time when the timer fired.

        This is calculated by `ready()` but is returned by `consume()`. If
        `None` it means `ready()` wasn't called and `consume()` will assert.
        `consume()` will set it back to `None` to tell `ready()` that it needs
        to wait again.
        """

        if auto_start:
            self.reset()

    def reset(self) -> None:
        """Reset the timer to start timing from now.

        If the timer was stopped, or not started yet, it will be started.

        This can only be called with a running loop, see the class
        documentation for more details.
        """
        self._stopped = False
        self._next_msg_time = asyncio.get_running_loop().time() + self._interval

    def stop(self) -> None:
        """Stop the timer.

        Once `stop` has been called, all subsequent calls to `ready()` will
        immediately return False and calls to `consume()` / `receive()` or any
        use of the async iterator interface will raise
        a `ReceiverStoppedError`.

        You can restart the timer with `reset()`.
        """
        self._stopped = True
        self._next_msg_time = None

    async def ready(self) -> bool:
        """Wait until the timer interval passed.

        Once a call to `ready()` has finished, the resulting drift must be read
        with a call to `consume()` (`receive()` or iterated over) to tell the
        timer it should wait for the next interval.

        The timer will remain ready (this method will return immediately)
        until it is consumed.

        Returns:
            Whether the timer is still running (if it was `stop()`ed, it will
                return `False`.

        Raises:
            RuntimeError: if it was called without a running loop.
        """
        # if there are messages waiting to be consumed, return immediately.
        if self._current_drift is not None:
            return True

        # If a stop was explicitly requested, we bail out.
        if self._stopped:
            return False

        # If there is no stop requested but we don't have a time for the next
        # message, then we reset() (so we start the timer as of now).
        if self._next_msg_time is None:
            self.reset()
            assert self._next_msg_time is not None, "This should be assigned by reset()"

        now = asyncio.get_running_loop().time()
        diff = self._next_msg_time - now
        if diff > 0:
            await asyncio.sleep(diff)
            now = asyncio.get_running_loop().time()
        self._current_drift = timedelta(seconds=now - self._next_msg_time)
        self._next_msg_time = self._next_msg_time + self._interval

        return True

    def consume(self) -> timedelta:
        """Return the latest drift once `ready()` is complete.

        Once the timer has fired (`ready()` is done), this method returns the
        difference between when the timer should have fired and the time when
        it actually fired. See the class documentation for more details.

        Returns:
            The time by which the timer has drifted while waiting for the next tick.

        Raises:
            ReceiverStoppedError: if the timer was stopped via `stop()`.
        """
        if self._stopped:
            raise ReceiverStoppedError(self)

        assert (
            self._current_drift is not None
        ), "calls to `consume()` must be follow a call to `ready()`"
        drift = self._current_drift
        self._current_drift = None
        return drift
