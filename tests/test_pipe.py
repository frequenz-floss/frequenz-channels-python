# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Tests for the Pipe class."""

import asyncio
import logging
import typing
from contextlib import AsyncExitStack, closing

import pytest
from frequenz.core.warnings import asserting_no_deprecations

from frequenz.channels import (
    BroadcastChannel,
    Pipe,
    Receiver,
    Sender,
    SenderClosedError,
    SenderError,
    TransientSenderError,
)

T = typing.TypeVar("T")


class Timeout:
    """Sentinel for timeout."""


async def receive_timeout(recv: Receiver[T], timeout: float = 0.1) -> T | type[Timeout]:
    """Receive message from receiver with timeout."""
    try:
        return await asyncio.wait_for(recv.receive(), timeout=timeout)
    except asyncio.TimeoutError:
        return Timeout


async def wait_stopped(pipe: Pipe[int]) -> None:
    """Wait until the task of a started pipe ends."""
    task = pipe._task  # pylint: disable=protected-access
    assert task is not None
    await asyncio.wait_for(task, timeout=1.0)


class FailingSender(Sender[int]):
    """A sender whose sends and `aclose()` fail."""

    async def send(self, message: int, /) -> None:
        """Fail to send."""
        raise SenderError("Sending failed", self)

    async def aclose(self) -> None:
        """Fail to close."""
        raise RuntimeError("Closing failed")


class ValueErrorSender(Sender[int]):
    """A sender whose sends raise an error that isn't a `SenderError`."""

    def __init__(self) -> None:
        """Initialize this sender."""
        self.closed = False

    async def send(self, message: int, /) -> None:
        """Fail to send."""
        raise ValueError("Sending failed")

    async def aclose(self) -> None:
        """Remember that this sender was closed."""
        self.closed = True


class BusySender(Sender[int]):
    """A sender that fails with a `TransientSenderError` for the first messages."""

    def __init__(self, busy_messages: int) -> None:
        """Initialize this sender.

        Args:
            busy_messages: How many messages to reject.
        """
        self.busy_messages = busy_messages
        self.sent: list[int] = []
        self.closed = False

    async def send(self, message: int, /) -> None:
        """Reject the first messages and keep the rest."""
        if self.busy_messages > 0:
            self.busy_messages -= 1
            raise TransientSenderError("Busy", self)
        self.sent.append(message)

    async def aclose(self) -> None:
        """Remember that this sender was closed."""
        self.closed = True


class UncloseableReceiver(Receiver[int]):
    """A receiver whose `close()` fails."""

    def __init__(self, receiver: Receiver[int]) -> None:
        """Wrap the given receiver."""
        self._receiver = receiver

    async def ready(self) -> bool:
        """Wait until the wrapped receiver is ready."""
        return await self._receiver.ready()

    def consume(self) -> int:
        """Return the wrapped receiver's message."""
        return self._receiver.consume()

    def close(self) -> None:
        """Fail to close."""
        raise NotImplementedError("close() is not supported")


def test_pipe_does_not_warn() -> None:
    """Ensure creating a pipe doesn't emit a deprecation warning."""
    _, source_receiver = BroadcastChannel[int](name="source")
    sender, _ = BroadcastChannel[int](name="forwarding")
    with asserting_no_deprecations():
        Pipe(source_receiver, sender)


async def test_pipe() -> None:
    """Test pipe."""
    sender_chan1, receiver_chan1 = BroadcastChannel[int](name="channel1")
    sender_chan2, receiver_chan2 = BroadcastChannel[int](name="channel2")

    async with Pipe(sender_chan2.subscribe(), sender_chan1.clone()):
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
    # Senders, receivers and Pipe are in AsyncExitStack
    # to close and stop them at the end.
    async with AsyncExitStack() as stack:
        source_sender, source_receiver = BroadcastChannel[int](name="source channel")
        stack.push_async_callback(source_sender.aclose)
        stack.enter_context(closing(source_receiver))

        forwarding_sender, receiver = BroadcastChannel[int](name="forwarding channel")
        stack.push_async_callback(forwarding_sender.aclose)
        stack.enter_context(closing(receiver))

        await stack.enter_async_context(Pipe(source_receiver, forwarding_sender))

        await source_sender.send(10)
        assert await receiver.receive() == 10


@pytest.mark.parametrize("close_pipe_on_send_error", [True, False])
async def test_pipe_keeps_sending_after_no_receivers(
    close_pipe_on_send_error: bool, caplog: pytest.LogCaptureFixture
) -> None:
    """Ensure a pipe drops messages while its channel has no receivers.

    A send without receivers is a `TransientSenderError`, so the pipe never stops for
    it, whatever `close_pipe_on_send_error` says.

    Args:
        close_pipe_on_send_error: The pipe's `close_pipe_on_send_error` argument.
        caplog: The fixture to capture log records.
    """
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender, receiver = BroadcastChannel[int](name="forwarding")
    receiver.close()

    pipe = Pipe(
        source_receiver, sender, close_pipe_on_send_error=close_pipe_on_send_error
    )
    await pipe.start()
    with caplog.at_level(logging.DEBUG, logger="frequenz.channels"):
        await source_sender.send(1)
        await asyncio.sleep(0)

        new_receiver = sender.subscribe()
        await source_sender.send(2)
        assert await receive_timeout(new_receiver) == 2

    assert source_sender.has_receivers
    assert [(r.levelno, r.exc_info) for r in caplog.records] == [(logging.DEBUG, None)]
    message = caplog.records[0].getMessage()
    assert "dropped a message" in message
    assert "has no receivers" in message
    await pipe.stop()


@pytest.mark.parametrize("close_pipe_on_send_error", [True, False])
async def test_pipe_keeps_sending_after_transient_error(
    close_pipe_on_send_error: bool, caplog: pytest.LogCaptureFixture
) -> None:
    """Ensure a pipe drops the message that failed with a `TransientSenderError`.

    Args:
        close_pipe_on_send_error: The pipe's `close_pipe_on_send_error` argument.
        caplog: The fixture to capture log records.
    """
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender = BusySender(busy_messages=2)

    pipe = Pipe(
        source_receiver, sender, close_pipe_on_send_error=close_pipe_on_send_error
    )
    await pipe.start()
    with caplog.at_level(logging.DEBUG, logger="frequenz.channels"):
        for message in (1, 2, 3, 4):
            await source_sender.send(message)
            await asyncio.sleep(0)

    assert sender.sent == [3, 4]
    assert not sender.closed
    assert source_sender.has_receivers
    assert [(r.levelno, r.exc_info) for r in caplog.records] == [
        (logging.WARNING, None),
        (logging.WARNING, None),
    ]
    assert "dropped a message" in caplog.records[0].getMessage()
    assert "Busy" in caplog.records[0].getMessage()
    await pipe.stop()


async def test_pipe_closes_both_ends_when_sending_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure a pipe closes its sender and receiver when it can't send."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")

    sender, receiver = BroadcastChannel[int](name="forwarding")
    receiver.close()
    await sender.aclose()

    pipe = Pipe(source_receiver, sender)
    await pipe.start()
    with caplog.at_level(logging.WARNING, logger="frequenz.channels"):
        await source_sender.send(1)
        await wait_stopped(pipe)

    assert not source_sender.has_receivers
    with pytest.raises(SenderClosedError):
        await sender.send(2)
    assert [r.levelno for r in caplog.records] == [logging.ERROR]
    assert "stopped" in caplog.records[0].getMessage()
    exc_info = caplog.records[0].exc_info
    assert exc_info is not None and isinstance(exc_info[1], SenderClosedError)


@pytest.mark.parametrize("close_pipe_on_send_error", [True, False])
async def test_pipe_closes_sender_when_receiver_stops(
    close_pipe_on_send_error: bool,
) -> None:
    """Ensure a pipe closes its sender when its receiver stops.

    Args:
        close_pipe_on_send_error: The pipe's `close_pipe_on_send_error` argument.
    """
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender, receiver = BroadcastChannel[int](name="forwarding")

    pipe = Pipe(
        source_receiver, sender, close_pipe_on_send_error=close_pipe_on_send_error
    )
    await pipe.start()
    await source_sender.send(1)
    assert await receive_timeout(receiver) == 1

    await source_sender.aclose()
    await wait_stopped(pipe)

    with pytest.raises(SenderClosedError):
        await sender.send(2)
    assert not receiver.has_senders


async def test_pipe_stop_leaves_both_ends_open() -> None:
    """Ensure stopping a pipe leaves its sender and receiver open."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender, receiver = BroadcastChannel[int](name="forwarding")

    pipe = Pipe(source_receiver, sender)
    await pipe.start()
    await asyncio.sleep(0)
    await pipe.stop()

    await sender.send(1)
    assert await receive_timeout(receiver) == 1
    await source_sender.send(2)
    assert await receive_timeout(source_receiver) == 2


async def test_pipe_leaves_both_ends_open_on_receive_exception() -> None:
    """Ensure an exception while receiving leaves a pipe's ends open."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender, receiver = BroadcastChannel[int](name="forwarding")

    def fail(_: int) -> int:
        raise ValueError("Mapping failed")

    pipe = Pipe(source_receiver.map(fail), sender)
    await pipe.start()
    await source_sender.send(1)
    with pytest.raises(ValueError, match="Mapping failed"):
        await wait_stopped(pipe)

    assert source_sender.has_receivers
    await sender.send(2)
    assert await receive_timeout(receiver) == 2


async def test_pipe_leaves_both_ends_open_on_send_exception() -> None:
    """Ensure an exception from sending that isn't a `SenderError` leaves both open."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender = ValueErrorSender()

    pipe = Pipe(source_receiver, sender)
    await pipe.start()
    await source_sender.send(1)
    with pytest.raises(ValueError, match="Sending failed"):
        await wait_stopped(pipe)

    assert source_sender.has_receivers
    assert not sender.closed


async def test_pipe_keeps_sending_after_send_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure a pipe that doesn't close on send errors logs each failed send."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")

    pipe = Pipe(source_receiver, FailingSender(), close_pipe_on_send_error=False)
    await pipe.start()
    with caplog.at_level(logging.WARNING, logger="frequenz.channels"):
        await source_sender.send(1)
        await asyncio.sleep(0)
        await source_sender.send(2)
        await asyncio.sleep(0)

    assert source_sender.has_receivers
    assert [r.levelno for r in caplog.records] == [logging.ERROR, logging.ERROR]
    assert "dropped a message" in caplog.records[0].getMessage()
    await pipe.stop()


async def test_pipe_closes_sender_when_receiver_cannot_close() -> None:
    """Ensure a failed send closes the sender even if the receiver can't close."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")
    sender, receiver = BroadcastChannel[int](name="forwarding")
    receiver.close()
    await sender.aclose()

    pipe = Pipe(UncloseableReceiver(source_receiver), sender)
    await pipe.start()
    await source_sender.send(1)
    with pytest.raises(NotImplementedError):
        await wait_stopped(pipe)

    with pytest.raises(SenderClosedError):
        await sender.send(2)


async def test_pipe_closes_receiver_when_sender_cannot_close() -> None:
    """Ensure a failed send closes the receiver even if the sender can't close."""
    source_sender, source_receiver = BroadcastChannel[int](name="source")

    pipe = Pipe(source_receiver, FailingSender())
    await pipe.start()
    await source_sender.send(1)
    with pytest.raises(RuntimeError, match="Closing failed"):
        await wait_stopped(pipe)

    assert not source_sender.has_receivers
