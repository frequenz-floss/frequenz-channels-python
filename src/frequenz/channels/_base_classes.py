# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Baseclasses for Channel Sender and Receiver."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Generic, Optional, TypeVar

from ._exceptions import ReceiverStoppedError

T = TypeVar("T")
U = TypeVar("U")


class Sender(ABC, Generic[T]):
    """A channel Sender."""

    @abstractmethod
    async def send(self, msg: T) -> None:
        """Send a message to the channel.

        Args:
            msg: The message to be sent.

        Raises:
            SenderError: if there was an error sending the message.
        """


class Receiver(ABC, Generic[T]):
    """A channel Receiver."""

    async def __anext__(self) -> T:
        """Await the next value in the async iteration over received values.

        Returns:
            The next value received.

        Raises:
            StopAsyncIteration: if the receiver stopped producing messages.
            ReceiverError: if there is some problem with the receiver.
        """
        try:
            await self.ready()
            return self.consume()
        except ReceiverStoppedError as exc:
            raise StopAsyncIteration() from exc

    @abstractmethod
    async def ready(self) -> bool:
        """Wait until the receiver is ready with a value or an error.

        Once a call to `ready()` has finished, the value should be read with
        a call to `consume()` (`receive()` or iterated over). The receiver will
        remain ready (this method will return immediately) until it is
        consumed.

        Returns:
            Whether the receiver is still active.
        """

    @abstractmethod
    def consume(self) -> T:
        """Return the latest value once `ready()` is complete.

        `ready()` must be called before each call to `consume()`.

        Returns:
            The next value received.

        Raises:
            ReceiverStoppedError: if the receiver stopped producing messages.
            ReceiverError: if there is some problem with the receiver.
        """

    def __aiter__(self) -> Receiver[T]:
        """Initialize the async iterator over received values.

        Returns:
            `self`, since no extra setup is needed for the iterator.
        """
        return self

    async def receive(self) -> T:
        """Receive a message from the channel.

        Returns:
            The received message.

        Raises:
            ReceiverStoppedError: if there is some problem with the receiver.
            ReceiverError: if there is some problem with the receiver.

        # noqa: DAR401 __cause__ (https://github.com/terrencepreilly/darglint/issues/181)
        """
        try:
            received = await self.__anext__()  # pylint: disable=unnecessary-dunder-call
        except StopAsyncIteration as exc:
            # If we already had a cause and it was the receiver was stopped,
            # then reuse that error, as StopAsyncIteration is just an artifact
            # introduced by __anext__.
            if (
                isinstance(exc.__cause__, ReceiverStoppedError)
                # pylint is not smart enough to figure out we checked above
                # this is a ReceiverStoppedError and thus it does have
                # a receiver member
                and exc.__cause__.receiver is self  # pylint: disable=no-member
            ):
                raise exc.__cause__
            raise ReceiverStoppedError(self) from exc
        return received

    def map(self, call: Callable[[T], U]) -> Receiver[U]:
        """Return a receiver with `call` applied on incoming messages.

        Args:
            call: function to apply on incoming messages.

        Returns:
            A `Receiver` to read results of the given function from.
        """
        return _Map(self, call)

    def into_peekable(self) -> Peekable[T]:
        """Convert the `Receiver` implementation into a `Peekable`.

        Once this function has been called, the receiver will no longer be
        usable, and calling `receive` on the receiver will raise an exception.

        Raises:
            NotImplementedError: when a `Receiver` implementation doesn't have
                a custom `into_peekable` implementation.
        """
        raise NotImplementedError("This receiver does not implement `into_peekable`")


class Peekable(ABC, Generic[T]):
    """A channel peekable.

    A Peekable provides a [peek()][frequenz.channels.Peekable] method that
    allows the user to get a peek at the latest value in the channel, without
    consuming anything.
    """

    @abstractmethod
    def peek(self) -> Optional[T]:
        """Return the latest value that was sent to the channel.

        Returns:
            The latest value received by the channel, and `None`, if nothing
                has been sent to the channel yet.
        """


class _Map(Receiver[U], Generic[T, U]):
    """Apply a transform function on a channel receiver.

    Has two generic types:

    - The input type: value type in the input receiver.
    - The output type: return type of the transform method.
    """

    def __init__(self, recv: Receiver[T], transform: Callable[[T], U]) -> None:
        """Create a `Transform` instance.

        Args:
            recv: The input receiver.
            transform: The function to run on the input
                data.
        """
        self._recv = recv
        self._transform = transform

    async def ready(self) -> bool:
        """Wait until the receiver is ready with a value or an error.

        Once a call to `ready()` has finished, the value should be read with
        a call to `consume()` (`receive()` or iterated over). The receiver will
        remain ready (this method will return immediately) until it is
        consumed.

        Returns:
            Whether the receiver is still active.
        """
        return await self._recv.ready()  # pylint: disable=protected-access

    def consume(self) -> U:
        """Return a transformed value once `ready()` is complete.

        Returns:
            The next value that was received.

        Raises:
            ChannelClosedError: if the underlying channel is closed.
        """
        return self._transform(self._recv.consume())  # pylint: disable=protected-access
