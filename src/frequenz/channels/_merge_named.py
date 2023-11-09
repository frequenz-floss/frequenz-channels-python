# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Merge messages coming from channels into a single stream containing name of message."""
import asyncio
import itertools
from collections import deque
from typing import Any, TypeVar

from ._receiver import Receiver, ReceiverStoppedError

_T = TypeVar("_T")


class MergeNamed(Receiver[tuple[str, _T]]):
    """Merge messages coming from multiple named channels into a single stream.

    When `MergeNamed` is no longer needed, then it should be stopped using
    `self.stop()` method. This will cleanup any internal pending async tasks.
    """

    def __init__(self, **kwargs: Receiver[_T]) -> None:
        """Create a `MergeNamed` instance.

        Args:
            **kwargs: sequence of channel receivers.
        """
        self._receivers: dict[str, Receiver[_T]] = kwargs
        """The sequence of channel receivers to get the messages to merge."""

        self._pending: set[asyncio.Task[Any]] = {
            asyncio.create_task(anext(recv), name=name)
            for name, recv in self._receivers.items()
        }
        """The set of pending tasks to merge messages."""

        self._results: deque[tuple[str, _T]] = deque(maxlen=len(self._receivers))
        """The internal buffer of merged messages."""

    def __del__(self) -> None:
        """Cleanup any pending tasks."""
        for task in self._pending:
            if not task.done() and task.get_loop().is_running():
                task.cancel()

    async def stop(self) -> None:
        """Stop the `MergeNamed` instance and cleanup any pending tasks."""
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
                self._results.append((name, result))
                self._pending.add(
                    # pylint: disable=unnecessary-dunder-call
                    asyncio.create_task(anext(self._receivers[name]), name=name)
                )

    def consume(self) -> tuple[str, _T]:
        """Return the latest value once `ready` is complete.

        Returns:
            The next key, value that was received.

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
            receivers = [str(p) for p in itertools.islice(self._receivers, 3)]
            receivers.append("…")
        else:
            receivers = [str(p) for p in self._receivers]
        return f"{type(self).__name__}:{','.join(receivers)}"

    def __repr__(self) -> str:
        """Return a string representation of this receiver."""
        return (
            f"{type(self).__name__}("
            f"{', '.join(f'{k}={v!r}' for k, v in self._receivers.items())})"
        )
