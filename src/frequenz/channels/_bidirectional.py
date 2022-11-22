# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""An abstraction to provide bi-directional communication between actors."""

from __future__ import annotations

from typing import Generic, TypeVar

from ._base_classes import Receiver, Sender, T, U
from ._broadcast import Broadcast

V = TypeVar("V")
W = TypeVar("W")


class Bidirectional(Generic[T, U]):
    """A wrapper class for simulating bidirectional channels."""

    class Handle(Sender[V], Receiver[W]):
        """A handle to a [Bidirectional][frequenz.channels.Bidirectional] instance.

        It can be used to send/receive values between the client and service.
        """

        def __init__(self, sender: Sender[V], receiver: Receiver[W]) -> None:
            """Create a `Bidirectional.Handle` instance.

            Args:
                sender: A sender to send values with.
                receiver: A receiver to receive values from.
            """
            self._sender = sender
            self._receiver = receiver

        async def send(self, msg: V) -> bool:
            """Send a value to the other side.

            Args:
                msg: The value to send.

            Returns:
                Whether the send was successful or not.
            """
            return await self._sender.send(msg)

        async def ready(self) -> None:
            """Wait until the receiver is ready with a value."""
            await self._receiver.ready()  # pylint: disable=protected-access

        def consume(self) -> W:
            """Return the latest value once `_ready` is complete.

            Returns:
                The next value that was received.
            """
            return self._receiver.consume()  # pylint: disable=protected-access

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

        self._client_handle = Bidirectional.Handle(
            self._request_channel.new_sender(),
            self._response_channel.new_receiver(),
        )
        self._service_handle = Bidirectional.Handle(
            self._response_channel.new_sender(),
            self._request_channel.new_receiver(),
        )

    @property
    def client_handle(self) -> Bidirectional.Handle[T, U]:
        """Get a `Handle` for the client side to use.

        Returns:
            Object to send/receive messages with.
        """
        return self._client_handle

    @property
    def service_handle(self) -> Bidirectional.Handle[U, T]:
        """Get a `Handle` for the service side to use.

        Returns:
            Object to send/receive messages with.
        """
        return self._service_handle
