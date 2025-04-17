# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Pipe between a receiver and a sender.

The `Pipe` class takes a receiver and a sender and creates a pipe between them by
forwarding all the messages received by the receiver to the sender.
"""

from __future__ import annotations

import asyncio
import typing

from .._generic import ChannelMessageT
from .._receiver import Receiver
from .._sender import Sender


class Pipe(typing.Generic[ChannelMessageT]):
    """A pipe between two channels.

    The `Pipe` class takes a receiver and a sender and creates a pipe between them
    by forwarding all the messages received by the receiver to the sender.

    Example:
        ```python
        import asyncio
        from contextlib import closing, aclosing, AsyncExitStack

        from frequenz.channels import Broadcast, Pipe, Receiver

        async def main() -> None:
            # Channels, receivers and Pipe are in AsyncExitStack
            # to close and stop them at the end.
            async with AsyncExitStack() as stack:
                source_channel = await stack.enter_async_context(
                    aclosing(Broadcast[int](name="source channel"))
                )
                source_receiver = stack.enter_context(closing(source_channel.new_receiver()))

                forwarding_channel = await stack.enter_async_context(
                    aclosing(Broadcast[int](name="forwarding channel"))
                )
                await stack.enter_async_context(
                    Pipe(source_receiver, forwarding_channel.new_sender())
                )

                receiver = stack.enter_context(closing(forwarding_channel.new_receiver()))

                source_sender = source_channel.new_sender()
                await source_sender.send(10)
                assert await receiver.receive() == 11

        asyncio.run(main())
        ```
    """

    def __init__(
        self, receiver: Receiver[ChannelMessageT], sender: Sender[ChannelMessageT]
    ) -> None:
        """Create a new pipe between two channels.

        Args:
            receiver: The receiver channel.
            sender: The sender channel.
        """
        self._sender = sender
        self._receiver = receiver
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> Pipe[ChannelMessageT]:
        """Enter the runtime context."""
        await self.start()
        return self

    async def __aexit__(
        self,
        _exc_type: typing.Type[BaseException] | None,
        _exc: BaseException | None,
        _tb: typing.Any,
    ) -> None:
        """Exit the runtime context."""
        await self.stop()

    async def start(self) -> None:
        """Start this pipe if it is not already running."""
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Stop this pipe."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        async for value in self._receiver:
            await self._sender.send(value)
