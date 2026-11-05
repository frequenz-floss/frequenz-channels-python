# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""A Sender for sending messages to multiple senders.

The [`RelaySender`][frequenz.channels.experimental.RelaySender] class takes multiple
senders and forwards all the messages sent to it, to the senders it was created with.
"""

import asyncio

from typing_extensions import override

from .._generic import SenderMessageT_contra
from .._sender import Sender


class RelaySender(Sender[SenderMessageT_contra]):
    """A [`Sender`][frequenz.channels.Sender] for sending messages to multiple senders.

    The [`RelaySender`][frequenz.channels.experimental.RelaySender] class takes multiple
    senders and forwards all the messages sent to it, to the senders it was created
    with.

    Example:
        ```python
        from frequenz.channels import BroadcastChannel
        from frequenz.channels.experimental import RelaySender

        sender1, receiver1 = BroadcastChannel[int](name="channel1")
        sender2, receiver2 = BroadcastChannel[int](name="channel2")

        tee_sender = RelaySender(sender1, sender2)

        await tee_sender.send(5)
        assert await receiver1.receive() == 5
        assert await receiver2.receive() == 5
        ```
    """

    def __init__(self, *senders: Sender[SenderMessageT_contra]) -> None:
        """Create a new [`RelaySender`][frequenz.channels.experimental.RelaySender].

        Args:
            *senders: The senders to send messages to.
        """
        self._senders = senders

    @override
    async def send(self, message: SenderMessageT_contra, /) -> None:
        """Send a message.

        Args:
            message: The message to be sent.
        """
        for sender in self._senders:
            await sender.send(message)

    @override
    async def aclose(self) -> None:
        """Close this sender."""
        await asyncio.gather(*(sender.aclose() for sender in self._senders))
