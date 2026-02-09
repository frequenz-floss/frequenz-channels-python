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
