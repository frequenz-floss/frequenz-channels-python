# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Merge messages coming from channels into a single stream containing name of message."""

import asyncio
from collections import deque
from typing import Any, Deque, Optional, Set, Tuple

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
            asyncio.create_task(recv.receive(), name=name)
            for name, recv in self._receivers.items()
        }
        self._results: Deque[Tuple[str, T]] = deque(maxlen=len(self._receivers))

    def __del__(self) -> None:
        """Cleanup any pending tasks."""
        for task in self._pending:
            task.cancel()

    async def receive(self) -> Optional[Tuple[str, T]]:
        """Wait until there's a message in any of the channels.

        Returns:
            The next message that was received, or `None`, if all channels have
                closed.
        """
        # we use a while loop to continue to wait for new data, in case the
        # previous `wait` completed because a channel was closed.
        while True:
            if len(self._results) > 0:
                return self._results.popleft()

            if len(self._pending) == 0:
                return None
            done, self._pending = await asyncio.wait(
                self._pending, return_when=asyncio.FIRST_COMPLETED
            )
            for item in done:
                name = item.get_name()
                result = item.result()
                # if channel is closed, don't add a task for it again.
                if result is None:
                    continue
                self._results.append((name, result))
                self._pending.add(
                    asyncio.create_task(self._receivers[name].receive(), name=name)
                )
