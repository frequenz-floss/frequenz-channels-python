# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A timer receiver that returns the timestamp every `interval`."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from frequenz.channels.base_classes import Receiver


class Timer(Receiver[datetime]):
    """A timer receiver that returns the timestamp every `interval` seconds.

    Primarily for use with [Select][frequenz.channels.Select].

    Example:
        When you want something to happen with a fixed period:

        ```python
        timer = channel.Timer(30.0)
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
        timer = channel.Timer(30.0)
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
        self._next_msg_time = datetime.now() + self._interval

    def reset(self) -> None:
        """Reset the timer to start timing from `now`."""
        self._next_msg_time = datetime.now() + self._interval

    def stop(self) -> None:
        """Stop the timer.

        Once `stop` has been called, all subsequent calls to
        [receive()][frequenz.channels.Timer.receive] will immediately return
        `None`.
        """
        self._stopped = True

    async def receive(self) -> Optional[datetime]:
        """Return the current time once the next tick is due.

        Returns:
            The time of the next tick or `None` if
                [stop()][frequenz.channels.Timer.stop] has been called on the
                timer.
        """
        if self._stopped:
            return None
        now = datetime.now()
        diff = self._next_msg_time - now
        while diff.total_seconds() > 0:
            await asyncio.sleep(diff.total_seconds())
            now = datetime.now()
            diff = self._next_msg_time - now

        self._next_msg_time = now + self._interval

        return now
