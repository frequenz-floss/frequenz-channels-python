"""Merge messages coming from channels into a single stream containing name of message.

Copyright
Copyright © 2022 Frequenz Energy-as-a-Service GmbH

License
MIT
"""

import asyncio
from collections import deque
from typing import Any, Deque, Optional, Set, Tuple

from frequenz.channels.base_classes import Message, Receiver, T


class MergeNamed(Receiver[Tuple[str, Message[T]]]):
    """Merge messages coming from multiple named receivers into a single stream."""

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
        self._results: Deque[Tuple[str, Message[T]]] = deque(maxlen=len(self._receivers))

    def __del__(self) -> None:
        """Cleanup any pending tasks."""
        for task in self._pending:
            task.cancel()

    async def receive(self) -> Optional[Tuple[str, Message[T]]]:
        """Wait until there's a message in any of the merged receivers.

        If any exception was received via the merged receivers it will NOT be
        raised, it will be returned instead, so the caller should check in any
        of the received message is an exception.

        Returns:
            The next message that was received, or None, if all channels have
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
                # TODO: Check if we can first put back all done tasks into
                # self._pending so they are picked up on the next receive()
                # call.
                #
                # Otherwise we could wrap the messages like it is done in
                # `Select`, so the user would call wrapped.result and that
                # would raise, so raising can be delayed to the point where the
                # value needs to be unwrapped.
                #
                # For now we are simply not raising any received exceptions.
                #
                # Raising a received exception here would mean messages can be
                # lost for the following done items. Because of this, we
                # collect the exceptions instead and return them.
                if exception := item.exception():
                    # Only Exceptions should come in the receiver, so we
                    # re-raise any other exception (BaseException) as it should
                    # be a programming error.
                    #
                    # Also we need this for type-checking, as task.exception is
                    # Optional[BaseException] and we want to store this in
                    # a Message[T], which is a Union[T, Exception].
                    assert isinstance(exception, Exception)
                    result = exception
                else:
                    result = item.result()
                # if channel is closed, don't add a task for it again.
                if result is None:
                    continue
                self._results.append((name, result))
                self._pending.add(
                    asyncio.create_task(self._receivers[name].receive(), name=name)
                )
