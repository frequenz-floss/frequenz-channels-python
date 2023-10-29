# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""An abstraction to provide bi-directional communication between actors."""

from __future__ import annotations

from typing import Generic, TypeVar

from ._base_classes import Receiver, Sender, T, U
from ._broadcast import Broadcast
from ._exceptions import ChannelError, ReceiverError, SenderError

V = TypeVar("V")
W = TypeVar("W")


class Bidirectional(Generic[T, U]):
    """A wrapper class for simulating bidirectional channels."""

    class Handle(Sender[V], Receiver[W]):
        """A handle to a [Bidirectional][frequenz.channels.Bidirectional] instance.

        It can be used to send/receive values between the client and service.
        """

        def __init__(
            self,
            channel: Bidirectional[V, W] | Bidirectional[W, V],
            sender: Sender[V],
            receiver: Receiver[W],
        ) -> None:
            """Create a `Bidirectional.Handle` instance.

            Args:
                channel: The underlying channel.
                sender: A sender to send values with.
                receiver: A receiver to receive values from.
            """
            self._chan: Bidirectional[V, W] | Bidirectional[W, V] = channel
            """The underlying channel."""

            self._sender: Sender[V] = sender
            """The sender to send values with."""

            self._receiver: Receiver[W] = receiver
            """The receiver to receive values from."""

        async def send(self, msg: V) -> None:
            """Send a value to the other side.

            Args:
                msg: The value to send.

            Raises:
                SenderError: if the underlying channel was closed.
                    A [ChannelClosedError][frequenz.channels.ChannelClosedError]
                    is set as the cause.
            """
            try:
                await self._sender.send(msg)
            except SenderError as err:
                # If this comes from a channel error, then we inject another
                # ChannelError having the information about the Bidirectional
                # channel to hide (at least partially) the underlying
                # Broadcast channels we use.
                if isinstance(err.__cause__, ChannelError):
                    this_chan_error = ChannelError(
                        f"Error in the underlying channel {err.__cause__.channel}: {err.__cause__}",
                        self._chan,  # pylint: disable=protected-access
                    )
                    this_chan_error.__cause__ = err.__cause__
                    err.__cause__ = this_chan_error
                raise err

        async def ready(self) -> bool:
            """Wait until the receiver is ready with a value or an error.

            Once a call to `ready()` has finished, the value should be read with
            a call to `consume()` (`receive()` or iterated over). The receiver will
            remain ready (this method will return immediately) until it is
            consumed.

            Returns:
                Whether the receiver is still active.
            """
            return await self._receiver.ready()  # pylint: disable=protected-access

        def consume(self) -> W:
            """Return the latest value once `_ready` is complete.

            Returns:
                The next value that was received.

            Raises:
                ReceiverStoppedError: if there is some problem with the receiver.
                ReceiverError: if there is some problem with the receiver.
            """
            try:
                return self._receiver.consume()  # pylint: disable=protected-access
            except ReceiverError as err:
                # If this comes from a channel error, then we inject another
                # ChannelError having the information about the Bidirectional
                # channel to hide (at least partially) the underlying
                # Broadcast channels we use.
                if isinstance(err.__cause__, ChannelError):
                    this_chan_error = ChannelError(
                        f"Error in the underlying channel {err.__cause__.channel}: {err.__cause__}",
                        self._chan,  # pylint: disable=protected-access
                    )
                    this_chan_error.__cause__ = err.__cause__
                    err.__cause__ = this_chan_error
                raise err

    def __init__(self, *, name: str) -> None:
        """Create a `Bidirectional` instance.

        Args:
            name: The name of the channel. This is used for logging, and it is used
                in the string representation and to name the underlying channels.
        """
        self._name: str = name
        """The name for the client, used to name the channels."""

        self._request_channel: Broadcast[T] = Broadcast(name=f"{self._name}:request")
        """The channel to send requests."""

        self._response_channel: Broadcast[U] = Broadcast(name=f"{self._name}:response")
        """The channel to send responses."""

        self._client_handle: Bidirectional.Handle[T, U] = Bidirectional.Handle(
            self,
            self._request_channel.new_sender(),
            self._response_channel.new_receiver(),
        )
        """The handle for the client side to send/receive values."""

        self._service_handle: Bidirectional.Handle[U, T] = Bidirectional.Handle(
            self,
            self._response_channel.new_sender(),
            self._request_channel.new_receiver(),
        )
        """The handle for the service side to send/receive values."""

    @property
    def is_closed(self) -> bool:
        """Whether this channel is closed.

        Any further attempts to use this channel after it is closed will result in an
        exception.

        As long as there is a way to send or receive data, the channel is considered
        open, even if the other side is closed, so this returns `False` if only both
        underlying channels are closed.
        """
        return self._request_channel.is_closed and self._response_channel.is_closed

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
