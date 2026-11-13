# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Pipe between a receiver and a sender.

The [`Pipe`][frequenz.channels.experimental.Pipe] class takes a receiver and a sender
and creates a pipe between them by forwarding all the messages received by the receiver
to the sender.
"""

from __future__ import annotations

import asyncio
import typing

from typing_extensions import deprecated

from .._generic import ChannelMessageT
from .._receiver import Receiver
from .._sender import Sender


@deprecated(
    "frequenz.channels.experimental.Pipe is deprecated and will be removed in v3.0.0. "
    "Use frequenz.channels.Pipe instead, but check how your code closes its sender and "
    "receiver first: the new one closes its sender when its receiver stops, and both "
    "ends when sending fails, while this one leaves them open."
)
class Pipe(typing.Generic[ChannelMessageT]):
    """A pipe between two channels.

    Deprecated:
        Deprecated since v2.0.0, and will be removed in v3.0.0.  Use
        [`frequenz.channels.Pipe`][] instead, after checking how your code closes the
        sender and the receiver: the new class closes them in cases where this one
        leaves them open, and drops messages that fail with a
        [`TransientSenderError`][frequenz.channels.TransientSenderError].

    The [`Pipe`][frequenz.channels.experimental.Pipe] class takes a receiver and a
    sender and creates a pipe between them by forwarding all the messages received by
    the receiver to the sender.

    [`frequenz.channels.Pipe`][] is a separate implementation that treats its endpoints
    differently, so moving to it can change how your code shuts down:

    * When its receiver stops, this pipe stops and leaves its sender open.
      [`frequenz.channels.Pipe`][] closes its sender too.
    * When sending fails with any [`SenderError`][frequenz.channels.SenderError], the
      exception ends the task of this pipe and both ends stay open.
      [`frequenz.channels.Pipe`][] logs the error and closes its sender and its
      receiver by default, unless it is a
      [`TransientSenderError`][frequenz.channels.TransientSenderError], like a
      [`SenderHasNoReceiversError`][frequenz.channels.SenderHasNoReceiversError]:
      then it logs it, drops the message and keeps forwarding.
    * [`frequenz.channels.Pipe`][] also takes `close_pipe_on_send_error=False`, which
      drops the message that failed with any other
      [`SenderError`][frequenz.channels.SenderError] and keeps forwarding the next
      ones.  This doesn't bring back the behavior of this class, which stops on the
      first send error.
    * [`stop()`][frequenz.channels.experimental.Pipe.stop] leaves both ends open in
      both.

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
            await self._sender.send(value)
