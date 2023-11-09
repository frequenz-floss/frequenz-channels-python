# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Merge messages coming from channels into a single stream."""

import asyncio
import itertools
from collections import deque
from typing import Any, TypeVar

from ._receiver import Receiver, ReceiverStoppedError

_T = TypeVar("_T")


def merge(*receivers: Receiver[_T]) -> Receiver[_T]:
    """Merge messages coming from multiple receivers into a single stream.

    Args:
        *receivers: The receivers to merge.

    Returns:
        A receiver that merges the messages coming from multiple receivers into a
            single stream.

    Raises:
        ValueError: if no receivers are provided.

    Example:
        For example, if there are two channel receivers with the same type,
        they can be awaited together, and their results merged into a single
        stream like this:

        ```python
        from frequenz.channels import Broadcast

        channel1 = Broadcast[int](name="input-chan-1")
        channel2 = Broadcast[int](name="input-chan-2")
        receiver1 = channel1.new_receiver()
        receiver2 = channel2.new_receiver()

        async for msg in merge(receiver1, receiver2):
            print(f"received {msg}")
        ```
    """
    if not receivers:
        raise ValueError("At least one receiver must be provided")

    return _Merge(*receivers, name="merge")


class _Merge(Receiver[_T]):
    """A receiver that merges messages coming from multiple receivers into a single stream."""

    def __init__(self, *receivers: Receiver[_T], name: str | None) -> None:
        """Create a `_Merge` instance.

        Args:
            *receivers: The receivers to merge.
            name: The name of the receiver. Used to to create the string representation
                of the receiver.
        """
        self._receivers: dict[str, Receiver[_T]] = {
            str(id): recv for id, recv in enumerate(receivers)
        }
        self._name: str = name if name is not None else type(self).__name__
        self._pending: set[asyncio.Task[Any]] = {
            asyncio.create_task(anext(recv), name=name)
            for name, recv in self._receivers.items()
        }
        self._results: deque[_T] = deque(maxlen=len(self._receivers))

    def __del__(self) -> None:
        """Cleanup any pending tasks."""
        for task in self._pending:
            if not task.done() and task.get_loop().is_running():
                task.cancel()

    async def stop(self) -> None:
        """Stop the `_Merge` instance and cleanup any pending tasks."""
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
                    asyncio.create_task(anext(self._receivers[name]), name=name)
                )

    def consume(self) -> _T:
        """Return the latest value once `ready` is complete.

        Returns:
            The next value that was received.

        Raises:
            ReceiverStoppedError: if the receiver stopped producing messages.
            ReceiverError: if there is some problem with the receiver.
        """
        if not self._results and not self._pending:
            raise ReceiverStoppedError(self)

        assert self._results, "`consume()` must be preceded by a call to `ready()`"

        return self._results.popleft()

    def __str__(self) -> str:
        """Return a string representation of this receiver."""
        if len(self._receivers) > 3:
            receivers = [str(p) for p in itertools.islice(self._receivers.values(), 3)]
            receivers.append("…")
        else:
            receivers = [str(p) for p in self._receivers.values()]
        return f"{self._name}:{','.join(receivers)}"

    def __repr__(self) -> str:
        """Return a string representation of this receiver."""
        return (
            f"{self._name}("
            f"{', '.join(f'{k}={v!r}' for k, v in self._receivers.items())})"
        )
