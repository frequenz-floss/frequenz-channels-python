# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A timer receiver that returns the timestamp every `interval`."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from .._base_classes import Receiver
from .._exceptions import ReceiverStoppedError


class Timer(Receiver[datetime]):
    """A timer receiver that returns the timestamp every `interval` seconds.

    Primarily for use with [Select][frequenz.channels.util.Select].

    The timestamp generated is a timezone-aware datetime using UTC as timezone.

    Example:
        When you want something to happen with a fixed period:

        ```python
        timer = Timer(30.0)
        select = Select(bat_1 = receiver1, timer = timer)
        while await select.ready():
            if msg := select.bat_1:
                if val := msg.inner:
                    process_data(val)
                else:
                    logging.warn("battery channel closed")
            if ts := select.timer:
                # something to do once every 30 seconds
                pass
        ```

        When you want something to happen when nothing else has happened in a
        certain interval:

        ```python
        timer = Timer(30.0)
        select = Select(bat_1 = receiver1, timer = timer)
        while await select.ready():
            timer.reset()
            if msg := select.bat_1:
                if val := msg.inner:
                    process_data(val)
                else:
                    logging.warn("battery channel closed")
            if ts := select.timer:
                # something to do if there's no battery data for 30 seconds
                pass
        ```
    """

    def __init__(self, interval: float) -> None:
        """Create a `Timer` instance.

        Args:
            interval: number of seconds between messages.
        """
        self._stopped = False
        self._interval = timedelta(seconds=interval)
        self._next_msg_time = datetime.now(timezone.utc) + self._interval
        self._now: Optional[datetime] = None

    def reset(self) -> None:
        """Reset the timer to start timing from `now`."""
        self._next_msg_time = datetime.now(timezone.utc) + self._interval

    def stop(self) -> None:
        """Stop the timer.

        Once `stop` has been called, all subsequent calls to
        [receive()][frequenz.channels.Receiver.receive] will immediately
        return `None`.
        """
        self._stopped = True

    async def ready(self) -> bool:
        """Wait until the receiver is ready with a value or an error.

        Once a call to `ready()` has finished, the value should be read with
        a call to `consume()` (`receive()` or iterated over). The receiver will
        remain ready (this method will return immediately) until it is
        consumed.

        Returns:
            Whether the receiver is still active.
        """
        # if there are messages waiting to be consumed, return immediately.
        if self._now is not None:
            return True

        if self._stopped:
            return False

        now = datetime.now(timezone.utc)
        diff = self._next_msg_time - now
        while diff.total_seconds() > 0:
            await asyncio.sleep(diff.total_seconds())
            now = datetime.now(timezone.utc)
            diff = self._next_msg_time - now
        self._now = now

        self._next_msg_time = self._now + self._interval

        return True

    def consume(self) -> datetime:
        """Return the latest value once `ready` is complete.

        Returns:
            The time of the next tick in UTC or `None` if
                [stop()][frequenz.channels.util.Timer.stop] has been called on
                the timer.

        Raises:
            ReceiverStoppedError: if the receiver stopped producing messages.
            ReceiverError: if there is some problem with the receiver.

        Changelog:
            * **v0.11.0:** Returns a timezone-aware datetime with UTC timezone
              instead of a native datetime object.
        """
        if self._stopped:
            raise ReceiverStoppedError(self)

        assert (
            self._now is not None
        ), "`consume()` must be preceeded by a call to `ready()`"
        now = self._now
        self._now = None
        return now
