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
