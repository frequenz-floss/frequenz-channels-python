# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Merge messages coming from channels into a single stream containing name of message."""

import asyncio
from collections import deque
from typing import Any, Deque, Set, Tuple

from .._base_classes import ChannelClosedError, Receiver, T


class MergeNamed(Receiver[Tuple[str, T]]):
    """Merge messages coming from multiple named channels into a single stream.

    When `MergeNamed` is no longer needed, then it should be stopped using
    `self.stop()` method. This will cleanup any internal pending async tasks.
    """

    def __init__(self, **kwargs: Receiver[T]) -> None:
        """Create a `MergeNamed` instance.

        Args:
            **kwargs: sequence of channel receivers.
        """
        self._receivers = kwargs
        self._pending: Set[asyncio.Task[Any]] = {
            asyncio.create_task(recv.__anext__(), name=name)
            for name, recv in self._receivers.items()
        }
        self._results: Deque[Tuple[str, T]] = deque(maxlen=len(self._receivers))

    def __del__(self) -> None:
        """Cleanup any pending tasks."""
        for task in self._pending:
            task.cancel()

    async def stop(self) -> None:
        """Stop the `MergeNamed` instance and cleanup any pending tasks."""
        for task in self._pending:
            task.cancel()
        await asyncio.gather(*self._pending, return_exceptions=True)
        self._pending = set()

    async def ready(self) -> None:
        """Wait until there's a message in any of the channels.

        Raises:
            ChannelClosedError: when all the channels are closed.
        """
        # we use a while loop to continue to wait for new data, in case the
        # previous `wait` completed because a channel was closed.
        while True:
            # if there are messages waiting to be consumed, return immediately.
            if len(self._results) > 0:
                return

            if len(self._pending) == 0:
                raise ChannelClosedError()
            done, self._pending = await asyncio.wait(
                self._pending, return_when=asyncio.FIRST_COMPLETED
            )
            for item in done:
                name = item.get_name()
                # if channel is closed, don't add a task for it again.
                if isinstance(item.exception(), StopAsyncIteration):
                    continue
                result = item.result()
                self._results.append((name, result))
                self._pending.add(
                    # pylint: disable=unnecessary-dunder-call
                    asyncio.create_task(self._receivers[name].__anext__(), name=name)
                )

    def consume(self) -> Tuple[str, T]:
        """Return the latest value once `ready` is complete.

        Raises:
            EOFError: When called before a call to `ready()` finishes.

        Returns:
            The next value that was received, along with its name.
        """
        assert self._results, "calls to `consume()` must be follow a call to `ready()`"

        return self._results.popleft()
