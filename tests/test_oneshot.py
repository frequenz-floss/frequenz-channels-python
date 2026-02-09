# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the oneshot channel."""

import asyncio

import pytest

from frequenz.channels import ReceiverStoppedError, SenderClosedError, oneshot


async def test_oneshot() -> None:
    """Test the oneshot function."""
    sender, receiver = oneshot(int)

    received: int | None = None

    async def receive_in_background() -> None:
        nonlocal received
        received = await receiver.receive()

    task = asyncio.create_task(receive_in_background())

    await sender.send(42)
    await task

    assert received == 42

    with pytest.raises(SenderClosedError):
        await sender.send(43)

    with pytest.raises(ReceiverStoppedError):
        await receiver.receive()
