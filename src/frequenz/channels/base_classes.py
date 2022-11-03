# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Baseclasses for Channel Sender and Receiver."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")
U = TypeVar("U")


class Sender(ABC, Generic[T]):
    """A channel Sender."""

    @abstractmethod
    async def send(self, msg: T) -> bool:
        """Send a message to the channel.

        Args:
            msg: The message to be sent.

        Returns:
            Whether the message was sent, based on whether the channel is open
                or not.
        """


class Receiver(ABC, Generic[T]):
    """A channel Receiver."""

    @abstractmethod
    async def receive(self) -> Optional[T]:
        """Receive a message from the channel.

        Returns:
            `None`, if the channel is closed, a message otherwise.
        """

    def __aiter__(self) -> Receiver[T]:
        """Initialize the async iterator over received values.

        Returns:
            `self`, since no extra setup is needed for the iterator.
        """
        return self

    async def __anext__(self) -> T:
        """Await the next value in the async iteration over received values.

        Returns:
            The next value received.

        Raises:
            StopAsyncIteration: if we receive `None`, i.e. if the underlying
                channel is closed.
        """
        received = await self.receive()
        if received is None:
            raise StopAsyncIteration
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
                a custom `get_peekable` implementation.
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


class BufferedReceiver(Receiver[T]):
    """A channel receiver with a buffer."""

    @abstractmethod
    def enqueue(self, msg: T) -> None:
        """Put a message into this buffered receiver's queue.

        Args:
            msg: The message to be added to the queue.
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

    async def receive(self) -> Optional[U]:
        """Return a transformed message received from the input channel.

        Returns:
            `None`, if the channel is closed, a message otherwise.
        """
        msg = await self._recv.receive()
        if msg is None:
            return None
        return self._transform(msg)
