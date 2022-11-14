# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Select the first among multiple AsyncIterators.

Expects AsyncIterator class to raise `StopAsyncIteration`
exception once no more messages are expected or the channel
is closed in case of `Receiver` class.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
)

logger = logging.Logger(__name__)
T = TypeVar("T")


@dataclass
class _Selected:
    """A wrapper class for holding values in `Select`.

    Using this wrapper class allows `Select` to inform user code when a
    receiver gets closed.
    """

    origin: AsyncIterator[Any]
    name: str
    result: Optional[Any]


class Select:
    """Select the next available message from a group of AsyncIterators.

    If `Select` was created with more `AsyncIterator` than what are read in
    the if-chain after each call to [ready()][frequenz.channels.Select.ready],
    messages coming in the additional async iterators are dropped, and
    a warning message is logged.

    [Receiver][frequenz.channels.Receiver]s also function as `AsyncIterator`.

    Example:
        For example, if there are two async iterators that you want to
        simultaneously wait on, this can be done with:

        ```python
        select = Select(name1 = receiver1, name2 = receiver2)
        while await select.ready():
            if msg := select.name1:
                if val := msg.inner:
                    # do something with `val`
                    pass
                else:
                    # handle closure of receiver.
                    pass
            elif msg := select.name2:
                # do something with `msg.inner`
                pass
        ```
    """

    def __init__(self, **kwargs: AsyncIterator[Any]) -> None:
        """Create a `Select` instance.

        Args:
            **kwargs: sequence of async iterators
        """
        self._receivers = kwargs
        self._pending: Dict[str, asyncio.Task[Any]] = dict()

        for name, recv in self._receivers.items():
            self._add_pending(name, recv)

    def __del__(self) -> None:
        """Cleanup any pending tasks."""
        for task in self._pending.values():
            task.cancel()

    def _add_pending(self, name: str, recv: AsyncIterator[Any]) -> None:
        async def pending_fun(name: str, recv: AsyncIterator[Any]) -> Tuple[str, Any]:
            try:
                # can replace __anext__() to anext() (Only Python 3.10>=)
                result = (
                    await recv.__anext__()
                )  # pylint: disable=unnecessary-dunder-call
            except StopAsyncIteration:
                result = None
            return name, result

        assert name not in self._pending
        self._pending[name] = asyncio.create_task(pending_fun(name, recv), name=name)

    async def ready(self) -> AsyncIterable[Any]:
        """Wait until there is a message in any of the async iterators.

        Returns `True` if there is a message available, and `False` if all
        async iterators have closed.

        Returns:
            Whether there are further messages or not.
        """
        print(f"PENDING: {[t.get_name() for t in self._pending.values()]}")
        while coro := next(asyncio.as_completed(self._pending.values()), None):
            name, result = await coro
            # Remove the done task from the pending
            del self._pending[name]
            print(f'>>> ready: {name=} {result=}')
            yield _Selected(origin=self._receivers[name], name=name, result=result)
            # if channel or AsyncIterator is closed
            # don't add a task for it again.
            if result is not None:
                self._add_pending(name, self._receivers[name])
            print(f"PENDING: {[t.get_name() for t in self._pending.values()]}")
