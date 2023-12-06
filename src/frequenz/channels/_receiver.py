# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Receiver interface and related exceptions.

# Receivers

Messages are received from [channels](/user-guide/channels/index.md) through
[Receiver][frequenz.channels.Receiver] objects. [Receivers][frequenz.channels.Receiver]
are usually created by calling `channel.new_receiver()` and are [async
iterators][typing.AsyncIterator], so the easiest way to receive values from them as
a stream is to use `async for`:

```python show_lines="6:"
from frequenz.channels import Anycast

channel = Anycast[int](name="test-channel")
receiver = channel.new_receiver()

async for value in receiver:
    print(value)
```

If you need to receive values in different places or expecting a particular
sequence, you can use the [`receive()`][frequenz.channels.Receiver.receive] method:

```python show_lines="6:"
from frequenz.channels import Anycast

channel = Anycast[int](name="test-channel")
receiver = channel.new_receiver()

first_value = await receiver.receive()
print(f"First value: {first_value}")

second_value = await receiver.receive()
print(f"Second value: {second_value}")
```

# Value Transformation

If you need to transform the received values, receivers provide a
[`map()`][frequenz.channels.Receiver.map] method to easily do so:

```python show_lines="6:"
from frequenz.channels import Anycast

channel = Anycast[int](name="test-channel")
receiver = channel.new_receiver()

async for value in receiver.map(lambda x: x + 1):
    print(value)
```

[`map()`][frequenz.channels.Receiver.map] returns a new full receiver, so you can
use it in any of the ways described above.

# Error Handling

!!! Tip inline end

    For more information about handling errors, please refer to the
    [Error Handling](/user-guide/error-handling/) section of the user guide.

If there is an error while receiving a message,
a [`ReceiverError`][frequenz.channels.ReceiverError] exception is raised for both
[`receive()`][frequenz.channels.Receiver.receive] method and async iteration
interface.

If the receiver has completely stopped (for example the underlying channel was
closed), a [`ReceiverStoppedError`][frequenz.channels.ReceiverStoppedError] exception
is raised by [`receive()`][frequenz.channels.Receiver.receive] method.

```python show_lines="6:"
from frequenz.channels import Anycast

channel = Anycast[int](name="test-channel")
receiver = channel.new_receiver()

try:
    await receiver.receive()
except ReceiverStoppedError as error:
    print("The receiver was stopped")
except ReceiverError as error:
    print(f"There was an error trying to receive: {error}")
```

When used as an async iterator, the iteration will just stop without raising an
exception:

```python show_lines="6:"
from frequenz.channels import Anycast

channel = Anycast[int](name="test-channel")
receiver = channel.new_receiver()

try:
    async for value in receiver:
        print(value)
except ReceiverStoppedError as error:
    print("Will never happen")
except ReceiverError as error:
    print(f"There was an error trying to receive: {error}")
# If we get here, the receiver was stopped
```

# Advanced Usage

!!! Warning inline end

    This section is intended for library developers that want to build other low-level
    abstractions on top of channels. If you are just using channels, you can safely
    ignore this section.

Receivers extend on the [async iterator protocol][typing.AsyncIterator] by providing
a [`ready()`][frequenz.channels.Receiver.ready] and
a [`consume()`][frequenz.channels.Receiver.consume] method.

The [`ready()`][frequenz.channels.Receiver.ready] method is used to await until the
receiver has a new value available, but without actually consuming it. The
[`consume()`][frequenz.channels.Receiver.consume] method consumes the next available
value and returns it.

[`ready()`][frequenz.channels.Receiver.ready] can be called multiple times, and it
will return immediately if the receiver is already ready.
[`consume()`][frequenz.channels.Receiver.consume] must be called only after
[`ready()`][frequenz.channels.Receiver.ready] is done and only once, until the next
call to [`ready()`][frequenz.channels.Receiver.ready].

Exceptions are never raised by [`ready()`][frequenz.channels.Receiver.ready], they
are always delayed until [`consume()`][frequenz.channels.Receiver.consume] is
called.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Generic, Self, TypeVar

from ._exceptions import Error

_T_co = TypeVar("_T_co", covariant=True)
_U_co = TypeVar("_U_co", covariant=True)


class Receiver(ABC, Generic[_T_co]):
    """An endpoint to receive messages."""

    async def __anext__(self) -> _T_co:
        """Await the next value in the async iteration over received values.

        Returns:
            The next value received.

        Raises:
            StopAsyncIteration: If the receiver stopped producing messages.
            ReceiverError: If there is some problem with the receiver.
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
    def consume(self) -> _T_co:
        """Return the latest value once `ready()` is complete.

        `ready()` must be called before each call to `consume()`.

        Returns:
            The next value received.

        Raises:
            ReceiverStoppedError: If the receiver stopped producing messages.
            ReceiverError: If there is some problem with the receiver.
        """

    def __aiter__(self) -> Self:
        """Initialize the async iterator over received values.

        Returns:
            `self`, since no extra setup is needed for the iterator.
        """
        return self

    async def receive(self) -> _T_co:
        """Receive a message from the channel.

        Returns:
            The received message.

        Raises:
            ReceiverStoppedError: If there is some problem with the receiver.
            ReceiverError: If there is some problem with the receiver.
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

    def map(self, call: Callable[[_T_co], _U_co]) -> Receiver[_U_co]:
        """Return a receiver with `call` applied on incoming messages.

        Tip:
            The returned receiver type won't have all the methods of the original
            receiver. If you need to access methods of the original receiver that are
            not part of the `Receiver` interface you should save a reference to the
            original receiver and use that instead.

        Args:
            call: function to apply on incoming messages.

        Returns:
            A `Receiver` to read results of the given function from.
        """
        return _Map(self, call)


class ReceiverError(Error, Generic[_T_co]):
    """An error originated in a [Receiver][frequenz.channels.Receiver].

    All exceptions generated by receivers inherit from this exception.
    """

    def __init__(self, message: str, receiver: Receiver[_T_co]):
        """Initialize this error.

        Args:
            message: An error message.
            receiver: The [Receiver][frequenz.channels.Receiver] where the
                error happened.
        """
        super().__init__(message)
        self.receiver: Receiver[_T_co] = receiver
        """The receiver where the error happened."""


class ReceiverStoppedError(ReceiverError[_T_co]):
    """A stopped [`Receiver`][frequenz.channels.Receiver] was used."""

    def __init__(self, receiver: Receiver[_T_co]):
        """Initialize this error.

        Args:
            receiver: The [Receiver][frequenz.channels.Receiver] where the
                error happened.
        """
        super().__init__(f"Receiver {receiver} was stopped", receiver)


class _Map(Receiver[_U_co], Generic[_T_co, _U_co]):
    """Apply a transform function on a channel receiver.

    Has two generic types:

    - The input type: value type in the input receiver.
    - The output type: return type of the transform method.
    """

    def __init__(
        self, receiver: Receiver[_T_co], transform: Callable[[_T_co], _U_co]
    ) -> None:
        """Initialize this receiver mapper.

        Args:
            receiver: The input receiver.
            transform: The function to run on the input data.
        """
        self._receiver: Receiver[_T_co] = receiver
        """The input receiver."""

        self._transform: Callable[[_T_co], _U_co] = transform
        """The function to run on the input data."""

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

    # We need a noqa here because the docs have a Raises section but the code doesn't
    # explicitly raise anything.
    def consume(self) -> _U_co:  # noqa: DOC502
        """Return a transformed value once `ready()` is complete.

        Returns:
            The next value that was received.

        Raises:
            ReceiverStoppedError: If the receiver stopped producing messages.
            ReceiverError: If there is some problem with the receiver.
        """
        return self._transform(
            self._receiver.consume()
        )  # pylint: disable=protected-access

    def __str__(self) -> str:
        """Return a string representation of the timer."""
        return f"{type(self).__name__}:{self._receiver}:{self._transform}"

    def __repr__(self) -> str:
        """Return a string representation of the timer."""
        return f"{type(self).__name__}({self._receiver!r}, {self._transform!r})"
