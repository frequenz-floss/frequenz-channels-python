# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the oneshot channel."""

import asyncio

import pytest

from frequenz.channels import (
    OneshotChannel,
    ReceiverStoppedError,
    SenderClosedError,
)


async def test_oneshot_recv_after_send() -> None:
    """Test the oneshot function.

    `receiver.receive()` is called after `sender.send()`.
    """
    sender, receiver = OneshotChannel[int]()

    await sender.send(42)
    assert await receiver.receive() == 42

    with pytest.raises(SenderClosedError):
        await sender.send(43)
    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()


async def test_oneshot_recv_before_send() -> None:
    """Test the oneshot function.

    `receiver.receive()` is called before `sender.send()`.
    """
    sender, receiver = OneshotChannel[int]()

    task = asyncio.create_task(receiver.receive())

    # Give the receiver a chance to start waiting
    await asyncio.sleep(0.0)

    await sender.send(42)
    assert await task == 42

    with pytest.raises(SenderClosedError):
        await sender.send(43)
    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()


async def test_oneshot_recv_after_sender_closed() -> None:
    """Test that closing sender works without sending a message.

    `receiver.receive()` is called after `sender.aclose()`.
    """
    sender, receiver = OneshotChannel[int]()

    await sender.aclose()

    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()
    with pytest.raises(SenderClosedError):
        await sender.send(4)


async def test_oneshot_recv_before_sender_closed() -> None:
    """Test that closing sender works without sending a message.

    `receiver.receive()` is called before `sender.aclose()`.
    """
    sender, receiver = OneshotChannel[int]()

    task = asyncio.create_task(receiver.receive())

    # Give the receiver a chance to start waiting
    await asyncio.sleep(0.0)

    await sender.aclose()

    with pytest.raises(ReceiverStoppedError):
        await task

    with pytest.raises(SenderClosedError):
        await sender.send(4)


async def test_oneshot_close_receiver_before_send() -> None:
    """Test closing the receiver before a message is sent."""
    sender, receiver = OneshotChannel[int]()

    receiver.close()

    assert not await receiver.ready()
    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()

    # The sender can still send, but the message is discarded.
    await sender.send(42)
    assert not await receiver.ready()
    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()
    with pytest.raises(SenderClosedError):
        await sender.send(43)


async def test_oneshot_close_receiver_after_send() -> None:
    """Test that a message sent before closing the receiver is still received."""
    sender, receiver = OneshotChannel[int]()

    await sender.send(42)
    receiver.close()

    assert await receiver.receive() == 42
    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()


async def test_oneshot_close_receiver_after_receive() -> None:
    """Test closing the receiver after the message was received."""
    sender, receiver = OneshotChannel[int]()

    await sender.send(42)
    assert await receiver.receive() == 42
    receiver.close()

    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()


async def test_oneshot_close_receiver_after_sender_closed() -> None:
    """Test closing the receiver after the sender was closed."""
    sender, receiver = OneshotChannel[int]()

    await sender.aclose()
    receiver.close()

    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()


async def test_oneshot_close_receiver_while_waiting() -> None:
    """Test that closing the receiver wakes up a pending `ready()`."""
    sender, receiver = OneshotChannel[int]()

    task = asyncio.create_task(receiver.ready())

    # Give the receiver a chance to start waiting
    await asyncio.sleep(0.0)

    receiver.close()
    assert not await asyncio.wait_for(task, timeout=1.0)

    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()

    await sender.send(42)
    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()


async def test_oneshot_close_mapped_receiver() -> None:
    """Test closing the receiver through a `map()` wrapper."""
    sender, receiver = OneshotChannel[int]()
    mapped = receiver.map(lambda x: x * 2)

    mapped.close()

    with pytest.raises(ReceiverStoppedError):
        await mapped.receive()
    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()

    await sender.send(21)
    with pytest.raises(ReceiverStoppedError):
        await mapped.receive()
