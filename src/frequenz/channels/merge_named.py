# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Merge messages coming from channels into a single stream containing name of message."""

import asyncio
from collections import deque
from typing import Any, Deque, Set, Tuple

from frequenz.channels.base_classes import Receiver, T


class MergeNamed(Receiver[Tuple[str, T]]):
    """Merge messages coming from multiple named channels into a single stream."""

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

    async def _ready(self) -> None:
        """Wait until there's a message in any of the channels.

        Raises:
            StopAsyncIteration: When the channel is closed.
        """
        # we use a while loop to continue to wait for new data, in case the
        # previous `wait` completed because a channel was closed.
        while True:
            # if there are messages waiting to be consumed, return immediately.
            if len(self._results) > 0:
                return

            if len(self._pending) == 0:
                raise StopAsyncIteration()
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

    def _get(self) -> Tuple[str, T]:
        """Return the latest value once `_ready` is complete.

        Raises:
            EOFError: When called before a call to `_ready()` finishes.

        Returns:
            The next value that was received, along with its name.
        """
        if not self._results:
            raise EOFError("_get called before _ready finished.")

        return self._results.popleft()
