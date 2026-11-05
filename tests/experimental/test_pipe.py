# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Tests for the Pipe class."""

import asyncio
import typing
from contextlib import AsyncExitStack, aclosing, closing

import pytest

from frequenz.channels import (
    Broadcast,
    BroadcastChannel,
    Receiver,
    Sender,
    SenderError,
)
from frequenz.channels.experimental import Pipe

T = typing.TypeVar("T")

DEPRECATION_MESSAGE = "frequenz.channels.experimental.Pipe is deprecated"
"""The start of the deprecation message, which the pytest filter matches."""


def make_pipe(receiver: Receiver[T], sender: Sender[T]) -> Pipe[T]:
    """Create a deprecated pipe, checking that it warns."""
    with pytest.deprecated_call(match=DEPRECATION_MESSAGE):
        return Pipe(receiver, sender)


class Timeout:
    """Sentinel for timeout."""


async def receive_timeout(recv: Receiver[T], timeout: float = 0.1) -> T | type[Timeout]:
    """Receive message from receiver with timeout."""
    try:
        return await asyncio.wait_for(recv.receive(), timeout=timeout)
    except asyncio.TimeoutError:
        return Timeout


async def test_pipe() -> None:
    """Test pipe."""
    channel1: Broadcast[int] = Broadcast(name="channel1")
    channel2: Broadcast[int] = Broadcast(name="channel2")

    sender_chan1 = channel1.new_sender()
    sender_chan2 = channel2.new_sender()
    receiver_chan1 = channel1.new_receiver()
    receiver_chan2 = channel2.new_receiver()

    async with make_pipe(channel2.new_receiver(), channel1.new_sender()):
        await sender_chan2.send(42)
        assert await receive_timeout(receiver_chan1) == 42
        assert await receive_timeout(receiver_chan2) == 42

        await sender_chan2.send(-2)
        assert await receive_timeout(receiver_chan1) == -2
        assert await receive_timeout(receiver_chan2) == -2

        await sender_chan1.send(43)
        assert await receive_timeout(receiver_chan1) == 43
        assert await receive_timeout(receiver_chan2) is Timeout

        await sender_chan2.send(5)
        assert await receive_timeout(receiver_chan1) == 5
        assert await receive_timeout(receiver_chan2) == 5

    await sender_chan2.send(5)
    assert await receive_timeout(receiver_chan1) is Timeout
    assert await receive_timeout(receiver_chan2) == 5


async def test_pipe_with_async_exit_stack() -> None:
    """Test how pipe should work with async exit stack."""
    # Channels, receivers and Pipe are in AsyncExitStack
    # to close and stop them at the end.
    async with AsyncExitStack() as stack:
        source_channel = await stack.enter_async_context(
            aclosing(Broadcast[int](name="source channel"))
        )
        source_receiver = stack.enter_context(closing(source_channel.new_receiver()))

        forwarding_channel = await stack.enter_async_context(
            aclosing(Broadcast[int](name="forwarding channel"))
        )
        await stack.enter_async_context(
            make_pipe(source_receiver, forwarding_channel.new_sender())
        )

        receiver = stack.enter_context(closing(forwarding_channel.new_receiver()))

        source_sender = source_channel.new_sender()
        await source_sender.send(10)
        assert await receiver.receive() == 10


async def test_pipe_deprecation_message() -> None:
    """Ensure the warning says what to use instead and what changes."""
    channel: Broadcast[int] = Broadcast(name="channel")
    with pytest.deprecated_call() as record:
        Pipe(channel.new_receiver(), channel.new_sender())

    message = str(record[0].message)
    assert message.startswith("frequenz.channels.experimental.Pipe is deprecated. ")
    assert "frequenz.channels.Pipe" in message
    assert "when its receiver stops" in message
    assert "when sending fails" in message
    assert "leaves them open" in message


async def test_pipe_leaves_sender_open_when_receiver_stops() -> None:
    """Ensure the deprecated pipe stops, but leaves its sender open."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender, receiver = BroadcastChannel[int](name="forwarding")

    pipe = make_pipe(source_receiver, sender)
    await pipe.start()
    await source_sender.send(1)
    assert await receive_timeout(receiver) == 1

    await source_sender.aclose()
    task = pipe._task  # pylint: disable=protected-access
    assert task is not None
    await asyncio.wait_for(task, timeout=1.0)

    await sender.send(2)
    assert await receive_timeout(receiver) == 2


class FailingSender(Sender[int]):
    """A sender whose sends fail with a `SenderError`."""

    def __init__(self) -> None:
        """Initialize this sender."""
        self.closed = False

    async def send(self, message: int, /) -> None:
        """Fail to send."""
        raise SenderError("Sending failed", self)

    async def aclose(self) -> None:
        """Remember that this sender was closed."""
        self.closed = True


async def test_pipe_leaves_both_ends_open_when_sending_fails() -> None:
    """Ensure the deprecated pipe lets a send error end its task and closes nothing."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender = FailingSender()

    pipe = make_pipe(source_receiver, sender)
    await pipe.start()
    await source_sender.send(1)
    task = pipe._task  # pylint: disable=protected-access
    assert task is not None
    with pytest.raises(SenderError, match="Sending failed"):
        await asyncio.wait_for(task, timeout=1.0)

    assert not sender.closed
    # The receiver is still open: the source channel still accepts messages.
    await source_sender.send(2)
    assert await receive_timeout(source_receiver) == 2


async def test_pipe_stop_leaves_both_ends_open() -> None:
    """Ensure stopping the deprecated pipe leaves its sender and receiver open."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender, receiver = BroadcastChannel[int](name="forwarding")

    pipe = make_pipe(source_receiver, sender)
    await pipe.start()
    await asyncio.sleep(0)
    await pipe.stop()

    await sender.send(1)
    assert await receive_timeout(receiver) == 1
    await source_sender.send(2)
    assert await receive_timeout(source_receiver) == 2
