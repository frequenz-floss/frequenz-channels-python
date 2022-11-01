# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""An abstraction to provide bi-directional communication between actors."""

from __future__ import annotations

from typing import Generic, Optional

from frequenz.channels.base_classes import Receiver, Sender, T, U
from frequenz.channels.broadcast import Broadcast


class Bidirectional(Generic[T, U]):
    """A wrapper class for simulating bidirectional channels."""

    def __init__(self, client_id: str, service_id: str) -> None:
        """Create a `Bidirectional` instance.

        Args:
            client_id: A name for the client, used to name the channels.
            service_id: A name for the service end of the channels.
        """
        self._client_id = client_id
        self._request_channel: Broadcast[T] = Broadcast(f"req_{service_id}_{client_id}")
        self._response_channel: Broadcast[U] = Broadcast(
            f"resp_{service_id}_{client_id}"
        )

        self._client_handle = BidirectionalHandle(
            self._request_channel.get_sender(),
            self._response_channel.get_receiver(),
        )
        self._service_handle = BidirectionalHandle(
            self._response_channel.get_sender(),
            self._request_channel.get_receiver(),
        )

    @property
    def client_handle(self) -> BidirectionalHandle[T, U]:
        """Get a BidirectionalHandle for the client to use.

        Returns:
            Object to send/receive messages with.
        """
        return self._client_handle

    @property
    def service_handle(self) -> BidirectionalHandle[U, T]:
        """Get a `BidirectionalHandle` for the service to use.

        Returns:
            Object to send/receive messages with.
        """
        return self._service_handle


class BidirectionalHandle(Sender[T], Receiver[U]):
    """A handle to a [Bidirectional][frequenz.channels.Bidirectional] instance.

    It can be used to send/receive values between the client and service.
    """

    def __init__(self, sender: Sender[T], receiver: Receiver[U]) -> None:
        """Create a `BidirectionalHandle` instance.

        Args:
            sender: A sender to send values with.
            receiver: A receiver to receive values from.
        """
        self._sender = sender
        self._receiver = receiver

    async def send(self, msg: T) -> bool:
        """Send a value to the other side.

        Args:
            msg: The value to send.

        Returns:
            Whether the send was successful or not.
        """
        return await self._sender.send(msg)

    async def receive(self) -> Optional[U]:
        """Receive a value from the other side.

        Returns:
            Received value, or `None` if the channels are closed.
        """
        return await self._receiver.receive()
