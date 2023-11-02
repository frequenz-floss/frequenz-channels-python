# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""An abstraction to provide bi-directional communication between actors."""

from __future__ import annotations

from typing import Generic, TypeVar

from ._exceptions import ChannelError
from ._receiver import Receiver, ReceiverError
from ._sender import Sender, SenderError
from .broadcast import Broadcast

_T = TypeVar("_T")
_U = TypeVar("_U")
_V = TypeVar("_V")
_W = TypeVar("_W")


class Bidirectional(Generic[_T, _U]):
    """A wrapper class for simulating bidirectional channels."""

    def __init__(self, *, name: str | None = None) -> None:
        """Create a `Bidirectional` instance.

        Args:
            name: A name for the client, used to name the channels.
        """
        self._name: str = f"{id(self):_}" if name is None else name
        """The name for the client, used to name the channels."""

        self._request_channel: Broadcast[_T] = Broadcast(name=f"{self._name}:request")
        """The channel to send requests."""

        self._response_channel: Broadcast[_U] = Broadcast(name=f"{self._name}:response")
        """The channel to send responses."""

        self._client_handle: Handle[_T, _U] = Handle(
            self,
            self._request_channel.new_sender(),
            self._response_channel.new_receiver(),
        )
        """The handle for the client side to send/receive values."""

        self._service_handle: Handle[_U, _T] = Handle(
            self,
            self._response_channel.new_sender(),
            self._request_channel.new_receiver(),
        )
        """The handle for the service side to send/receive values."""

    @property
    def name(self) -> str:
        """The name of this channel.

        This is for debugging purposes, it will be shown in the string representation
        of this channel.
        """
        return self._name

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
    def client_handle(self) -> Handle[_T, _U]:
        """Get a `Handle` for the client side to use.

        Returns:
            Object to send/receive messages with.
        """
        return self._client_handle

    @property
    def service_handle(self) -> Handle[_U, _T]:
        """Get a `Handle` for the service side to use.

        Returns:
            Object to send/receive messages with.
        """
        return self._service_handle

    def __str__(self) -> str:
        """Return a string representation of this channel."""
        return f"{type(self).__name__}:{self._name}"

    def __repr__(self) -> str:
        """Return a string representation of this channel."""
        return (
            f"{type(self).__name__}(name={self._name!r}):<"
            f"request_channel={self._request_channel!r}, "
            f"response_channel={self._response_channel!r}>"
        )


class Handle(Sender[_V], Receiver[_W]):
    """A handle to a [Bidirectional][frequenz.channels.bidirectional.Bidirectional] instance.

    It can be used to send/receive values between the client and service.
    """

    def __init__(
        self,
        channel: Bidirectional[_V, _W] | Bidirectional[_W, _V],
        sender: Sender[_V],
        receiver: Receiver[_W],
    ) -> None:
        """Create a `Handle` instance.

        Args:
            channel: The underlying channel.
            sender: A sender to send values with.
            receiver: A receiver to receive values from.
        """
        self._chan: Bidirectional[_V, _W] | Bidirectional[_W, _V] = channel
        """The underlying channel."""

        self._sender: Sender[_V] = sender
        """The sender to send values with."""

        self._receiver: Receiver[_W] = receiver
        """The receiver to receive values from."""

    async def send(self, msg: _V) -> None:
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

    def consume(self) -> _W:
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

    def __str__(self) -> str:
        """Return a string representation of this handle."""
        return f"{type(self).__name__}:{self._chan}"

    def __repr__(self) -> str:
        """Return a string representation of this handle."""
        return (
            f"{type(self).__name__}(channel={self._chan!r}, "
            f"sender={self._sender!r}, receiver={self._receiver!r})"
        )
