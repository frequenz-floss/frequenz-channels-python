# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""A channel that can send a single message."""

from __future__ import annotations

import asyncio
import typing

from ._generic import ChannelMessageT
from ._receiver import Receiver, ReceiverStoppedError
from ._sender import Sender, SenderClosedError


class _Empty:
    """A sentinel indicating that no message has been sent."""


_EMPTY = _Empty()


class _Oneshot(typing.Generic[ChannelMessageT]):
    """Internal representation of a one-shot channel.

    A one-shot channel is a channel that can only send one message. After the first
    message is sent, the sender is closed and any further attempts to send a message
    will raise a [`SenderClosedError`][..SenderClosedError].
    """

    def __init__(self) -> None:
        """Create a new one-shot channel."""
        self.message: ChannelMessageT | _Empty = _EMPTY
        self.closed: bool = False
        self.drained: bool = False
        self.event: asyncio.Event = asyncio.Event()


class OneshotSender(Sender[ChannelMessageT]):
    """A sender for a one-shot channel."""

    def __init__(self, channel: _Oneshot[ChannelMessageT]) -> None:
        """Initialize this sender."""
        self._channel = channel

    async def send(self, message: ChannelMessageT, /) -> None:
        """Send a message through this sender.

        Args:
            message: The message to send.

        Raises:
            SenderClosedError: If the sender has already been closed.
        """
        if self._channel.closed:
            raise SenderClosedError(self)
        self._channel.message = message
        self._channel.closed = True
        self._channel.event.set()

    async def aclose(self) -> None:
        """Close this sender."""
        self._channel.closed = True
        if isinstance(self._channel.message, _Empty):
            self._channel.drained = True
        self._channel.event.set()


class OneshotReceiver(Receiver[ChannelMessageT]):
    """A receiver for a one-shot channel."""

    def __init__(self, channel: _Oneshot[ChannelMessageT]) -> None:
        """Initialize this receiver."""
        self._channel = channel

    async def ready(self) -> bool:
        """Wait until a message is ready to be received.

        Returns:
            `True` if a message is ready to be received, `False` if the sender
                is closed and no message will be sent.
        """
        if self._channel.drained:
            return False
        while not self._channel.closed:
            await self._channel.event.wait()
        if isinstance(self._channel.message, _Empty):
            return False
        return True

    def consume(self) -> ChannelMessageT:
        """Consume a message from this receiver.

        Returns:
            The message that was sent through this channel.

        Raises:
            ReceiverStoppedError: If the sender was closed without sending a message.
        """
        if self._channel.drained:
            raise ReceiverStoppedError(self)

        assert not isinstance(
            self._channel.message, _Empty
        ), "`consume()` must be preceded by a call to `ready()`."

        self._channel.drained = True
        self._channel.event.clear()
        return self._channel.message


class OneshotChannel(
    tuple[OneshotSender[ChannelMessageT], OneshotReceiver[ChannelMessageT]]
):
    """A channel that can send a single message.

    A one-shot channel is a channel that can only send one message. After the first
    message is sent, the sender is closed and any further attempts to send a message
    will raise a [`SenderClosedError`][..SenderClosedError].

    Example: Sending a message from one task to another
        ```python
        import asyncio

        from frequenz.channels import OneshotChannel, OneshotSender

        async def send(sender: OneshotSender[int]) -> None:
            await sender.send(42)

        async def main() -> None:
            sender, receiver = OneshotChannel[int]()

            async with asyncio.TaskGroup() as tg:
                tg.create_task(send(sender))
                assert await receiver.receive() == 42

        asyncio.run(main())
        ```
    """

    def __new__(cls) -> OneshotChannel[ChannelMessageT]:
        """Create a new one-shot channel."""
        channel = _Oneshot[ChannelMessageT]()

        return tuple.__new__(cls, (OneshotSender(channel), OneshotReceiver(channel)))
