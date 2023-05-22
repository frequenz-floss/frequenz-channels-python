# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Merge messages coming from channels into a single stream."""

import asyncio
from collections import deque
from typing import Any, Deque, Set

from .._base_classes import Receiver, T
from .._exceptions import ReceiverStoppedError


class Merge(Receiver[T]):
    """Merge messages coming from multiple channels into a single stream.

    Example:
        For example, if there are two channel receivers with the same type,
        they can be awaited together, and their results merged into a single
        stream, by using `Merge` like this:

        ```python
        from frequenz.channels import Broadcast

        channel1 = Broadcast[int]("input-chan-1")
        channel2 = Broadcast[int]("input-chan-2")
        receiver1 = channel1.new_receiver()
        receiver2 = channel2.new_receiver()

        merge = Merge(receiver1, receiver2)
        while msg := await merge.receive():
            # do something with msg
            pass
        ```

        When `merge` is no longer needed, then it should be stopped using
        `self.stop()` method. This will cleanup any internal pending async tasks.
    """

    def __init__(self, *args: Receiver[T]) -> None:
        """Create a `Merge` instance.

        Args:
            *args: sequence of channel receivers.
        """
        self._receivers = {str(id): recv for id, recv in enumerate(args)}
        self._pending: Set[asyncio.Task[Any]] = {
            asyncio.create_task(recv.__anext__(), name=name)
            for name, recv in self._receivers.items()
        }
        self._results: Deque[T] = deque(maxlen=len(self._receivers))

    def __del__(self) -> None:
        """Cleanup any pending tasks."""
        for task in self._pending:
            if not task.done() and task.get_loop().is_running():
                task.cancel()

    async def stop(self) -> None:
        """Stop the `Merge` instance and cleanup any pending tasks."""
        for task in self._pending:
            task.cancel()
        await asyncio.gather(*self._pending, return_exceptions=True)
        self._pending = set()

    async def ready(self) -> bool:
        """Wait until the receiver is ready with a value or an error.

        Once a call to `ready()` has finished, the value should be read with
        a call to `consume()` (`receive()` or iterated over). The receiver will
        remain ready (this method will return immediately) until it is
        consumed.

        Returns:
            Whether the receiver is still active.
        """
        # we use a while loop to continue to wait for new data, in case the
        # previous `wait` completed because a channel was closed.
        while True:
            # if there are messages waiting to be consumed, return immediately.
            if len(self._results) > 0:
                return True

            # if there are no more pending receivers, we return immediately.
            if len(self._pending) == 0:
                return False

            done, self._pending = await asyncio.wait(
                self._pending, return_when=asyncio.FIRST_COMPLETED
            )
            for item in done:
                name = item.get_name()
                # if channel is closed, don't add a task for it again.
                if isinstance(item.exception(), StopAsyncIteration):
                    continue
                result = item.result()
                self._results.append(result)
                self._pending.add(
                    # pylint: disable=unnecessary-dunder-call
                    asyncio.create_task(self._receivers[name].__anext__(), name=name)
                )

    def consume(self) -> T:
        """Return the latest value once `ready` is complete.

        Returns:
            The next value that was received.

        Raises:
            ReceiverStoppedError: if the receiver stopped producing messages.
            ReceiverError: if there is some problem with the receiver.
        """
        if not self._results and not self._pending:
            raise ReceiverStoppedError(self)

        assert self._results, "`consume()` must be preceeded by a call to `ready()`"

        return self._results.popleft()
