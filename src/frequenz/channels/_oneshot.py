# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""A channel that can send a single message."""

import asyncio
import typing

from ._generic import ChannelMessageT
from ._receiver import Receiver, ReceiverStoppedError
from ._sender import Sender, SenderClosedError


def oneshot(
    message_type: type[ChannelMessageT],  # pylint: disable=unused-argument
) -> tuple[Sender[ChannelMessageT], Receiver[ChannelMessageT]]:
    """Create a one-shot channel.

    A one-shot channel is a channel that can only send one message. After the first
    message is sent, the sender is closed and any further attempts to send a message
    will raise a `SenderClosedError`.

    Args:
        message_type: The type of messages that can be sent through this channel.

    Returns:
        A tuple of a sender and a receiver for this channel.
    """
    channel = _OneShot[ChannelMessageT]()
    return _OneShotSender(channel), _OneShotReceiver(channel)


class _Empty:
    pass


_EMPTY = _Empty()


class _OneShot(typing.Generic[ChannelMessageT]):
    """A one-shot channel.

    A one-shot channel is a channel that can only send one message. After the first
    message is sent, the sender is closed and any further attempts to send a message
    will raise a `SenderClosedError`.
    """

    def __init__(self) -> None:
        """Create a new one-shot channel."""
        self.message: ChannelMessageT | _Empty = _EMPTY
        self.sent = False
        self.drained = False
        self.event = asyncio.Event()


class _OneShotSender(Sender[ChannelMessageT]):
    def __init__(self, channel: _OneShot[ChannelMessageT]) -> None:
        self._channel = channel

    async def send(self, message: ChannelMessageT, /) -> None:
        if self._channel.sent:
            raise SenderClosedError(self)
        self._channel.message = message
        self._channel.sent = True
        self._channel.event.set()

    def close(self) -> None:
        self._channel.sent = True


class _OneShotReceiver(Receiver[ChannelMessageT]):
    def __init__(self, channel: _OneShot[ChannelMessageT]) -> None:
        self._channel = channel

    async def ready(self) -> bool:
        if self._channel.drained:
            return False
        if not self._channel.sent:
            await self._channel.event.wait()
        return True

    def consume(self) -> ChannelMessageT:
        if self._channel.drained:
            raise ReceiverStoppedError(self)
        if isinstance(self._channel.message, _Empty):
            raise ReceiverStoppedError(self)

        self._channel.drained = True
        self._channel.event.clear()
        return self._channel.message
