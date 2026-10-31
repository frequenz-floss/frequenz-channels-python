# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Pipe between a receiver and a sender.

The [`Pipe`][frequenz.channels.experimental.Pipe] class takes a receiver and a sender
and creates a pipe between them by forwarding all the messages received by the receiver
to the sender.
"""

from __future__ import annotations

import asyncio
import logging
import typing

from .._generic import ChannelMessageT
from .._receiver import Receiver
from .._sender import NoReceiversError, Sender, SenderError

_logger = logging.getLogger(__name__)


class Pipe(typing.Generic[ChannelMessageT]):
    """A pipe between two channels.

    The [`Pipe`][frequenz.channels.experimental.Pipe] class takes a receiver and a
    sender and creates a pipe between them by forwarding all the messages received by
    the receiver to the sender.

    When its receiver stops, the pipe closes its sender and stops.  If sending fails
    with a [`SenderError`][frequenz.channels.SenderError], for example because the
    sender's channel has no receivers, the pipe closes both its sender and its
    receiver, and stops.  It logs the error: a
    [`NoReceiversError`][frequenz.channels.NoReceiversError] as a warning, and any
    other error with its traceback.

    [`stop()`][frequenz.channels.experimental.Pipe.stop] leaves both open.  Give the
    pipe a clone of the sender if you still need to send after the pipe stops on its
    own.

    Example:
        ```python
        import asyncio
        from contextlib import closing, AsyncExitStack

        from frequenz.channels import BroadcastChannel
        from frequenz.channels.experimental import Pipe

        async def main() -> None:
            # Senders, receivers and Pipe are in AsyncExitStack
            # to close and stop them at the end.
            async with AsyncExitStack() as stack:
                source_sender, source_receiver = BroadcastChannel[int](
                    name="source channel"
                )
                stack.push_async_callback(source_sender.aclose)
                stack.enter_context(closing(source_receiver))

                forwarding_sender, receiver = BroadcastChannel[int](
                    name="forwarding channel"
                )
                stack.push_async_callback(forwarding_sender.aclose)
                stack.enter_context(closing(receiver))

                await stack.enter_async_context(Pipe(source_receiver, forwarding_sender))

                await source_sender.send(10)
                assert await receiver.receive() == 10

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
            try:
                await self._sender.send(value)
            except NoReceiversError:
                _logger.warning(
                    "Pipe from [%s] to [%s] stopped: the sender has no receivers",
                    self._receiver,
                    self._sender,
                )
            except SenderError:
                _logger.exception(
                    "Pipe from [%s] to [%s] stopped: sending failed",
                    self._receiver,
                    self._sender,
                )
            else:
                continue
            try:
                await self._sender.aclose()
            finally:
                self._receiver.close()
            return
        await self._sender.aclose()
