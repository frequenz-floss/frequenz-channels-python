# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Select the first among multiple Receivers.

Expects Receiver class to raise `StopAsyncIteration`
exception once no more messages are expected or the channel
is closed in case of `Receiver` class.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any, Dict, Set, TypeVar

from .._base_classes import Receiver

logger = logging.Logger(__name__)
T = TypeVar("T")


class Select:
    """Select the next available message from a group of Receivers.

    If `Select` was created with more `Receiver` than what are read in
    the if-chain after each call to
    [ready()][frequenz.channels.util.Select.ready], messages coming in the
    additional receivers are dropped, and a warning message is logged.

    [Receiver][frequenz.channels.Receiver]s also function as `Receiver`.

    When Select is no longer needed, then it should be stopped using
    `self.stop()` method. This would cleanup any internal pending async tasks.

    Example:
        For example, if there are two receivers that you want to
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

    def __init__(self, *receivers: Receiver[Any]) -> None:
        """Create a `Select` instance.

        Args:
            *receivers: A set of receivers to select from.
        """
        self._receivers: Dict[str, Receiver[Any]] = {
            f"0x{id(r):x}": r for r in receivers
        }
        self._pending: Set[asyncio.Task[bool]] = set()

        for name, recv in self._receivers.items():
            self._pending.add(asyncio.create_task(recv.ready(), name=name))

    def __del__(self) -> None:
        """Cleanup any pending tasks."""
        for task in self._pending:
            task.cancel()

    async def stop(self) -> None:
        """Stop the `Select` instance and cleanup any pending tasks."""
        for task in self._pending:
            task.cancel()
        await asyncio.gather(*self._pending, return_exceptions=True)
        self._pending = set()

    async def ready(self) -> AsyncIterator[Set[Receiver[Any]]]:
        """Wait until there is a message in any of the receivers.

        Returns `True` if there is a message available, and `False` if all
        receivers have closed.

        Yields:
            A set with the receivers that are ready to be consumed.

        Raises:
            BaseException: if the receivers raise any exceptions.

        # noqa: DAR401 exc (https://github.com/terrencepreilly/darglint/issues/181)
        """
        while self._pending:
            done, self._pending = await asyncio.wait(
                self._pending, return_when=asyncio.FIRST_COMPLETED
            )
            ready_set: Set[Receiver[Any]] = set()
            for task in done:
                name = task.get_name()
                recv = self._receivers[name]
                # This will raise if there was an exception in the task
                # Colloect or not collect exceptions
                exc = task.exception()
                if exc is not None:
                    raise exc
                ready_set.add(recv)

            yield ready_set

            for task in done:
                receiver_active = task.result()
                if not receiver_active:
                    continue
                name = task.get_name()
                recv = self._receivers[name]
                self._pending.add(asyncio.create_task(recv.ready(), name=name))
