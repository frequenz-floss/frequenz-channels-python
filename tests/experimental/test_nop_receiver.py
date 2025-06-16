# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""Tests for the NopReceiver."""

import asyncio
from contextlib import closing

import pytest

from frequenz.channels import ReceiverError
from frequenz.channels._receiver import ReceiverStoppedError
from frequenz.channels.experimental import NopReceiver


async def test_never_ready() -> None:
    """Test that the receiver is never ready."""
    # When it is not closed, `ready()` should never return.
    with closing(NopReceiver[int]()) as receiver:
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(receiver.ready(), timeout=0.1)

    # When it is closed, `ready()` should return False.
    receiver = NopReceiver[int]()
    receiver.close()
    assert await asyncio.wait_for(receiver.ready(), timeout=0.1) is False


async def test_consuming_raises() -> None:
    """Test that consume raises an error."""
    # When it is not closed, `consume()` should raise a ReceiverError.
    with closing(NopReceiver[int]()) as receiver:
        with pytest.raises(ReceiverError):
            receiver.consume()

    # When it is closed, `consume()` should raise a ReceiverStoppedError.
    receiver = NopReceiver[int]()
    receiver.close()
    with pytest.raises(ReceiverStoppedError):
        receiver.consume()


async def test_close_method_effect_on_ready() -> None:
    """Test `ready()` terminates when the receiver is closed.

    When the receiver is closed, `ready()` should return False.
    This test verifies that:
    1. `ready()` returns False immediately after `close()` is called
    2. `ready()` and `close()` can be called multiple times
    """
    receiver = NopReceiver[int]()

    # Create a task that waits for the receiver to be ready.
    task = asyncio.create_task(receiver.ready())

    # Wait for the task to start.
    await asyncio.sleep(0.1)

    # Close the receiver and wait for the task to complete.
    receiver.close()
    assert await asyncio.wait_for(task, timeout=0.1) is False

    # Second call to `close()` or `ready()` should not raise an error.
    receiver.close()
    assert await asyncio.wait_for(receiver.ready(), timeout=0.1) is False
