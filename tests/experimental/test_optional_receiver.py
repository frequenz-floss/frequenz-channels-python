# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""Tests for the OptionalReceiver class."""

import asyncio
from contextlib import aclosing, closing

import pytest

from frequenz.channels import Broadcast, ReceiverError, ReceiverStoppedError
from frequenz.channels.experimental import OptionalReceiver


async def test_receiver_with_none_does_not_end() -> None:
    """Test that the receiver with None does not end."""
    with closing(OptionalReceiver[int](None)) as receiver:
        assert not receiver.is_set()

        with pytest.raises(TimeoutError):
            await asyncio.wait_for(receiver.ready(), timeout=0.3)


async def test_receiver_with_none_raises_error_when_consuming() -> None:
    """Test that the receiver with None raises an error when consuming."""
    with closing(OptionalReceiver[int](None)) as receiver:
        assert not receiver.is_set()

        with pytest.raises(ReceiverError):
            receiver.consume()


async def test_receiver_with_underlying_receiver_forwards_messages() -> None:
    """Test that the receiver forwards messages."""
    async with aclosing(Broadcast[int](name="test")) as channel:
        with closing(OptionalReceiver[int](channel.new_receiver())) as receiver:
            assert receiver.is_set()

            sender = channel.new_sender()

            await sender.send(5)
            value = await asyncio.wait_for(receiver.receive(), timeout=0.1)
            assert value == 5

            await sender.send(100)
            value = await asyncio.wait_for(receiver.receive(), timeout=0.1)
            assert value == 100


async def test_receiver_ends_when_underlying_receiver_ends() -> None:
    """Test that the receiver ends when the underlying receiver ends."""
    async with aclosing(Broadcast[int](name="test")) as channel:
        with (
            closing(channel.new_receiver()) as receiver,
            closing(OptionalReceiver[int](receiver)) as optional_receiver,
        ):
            assert optional_receiver.is_set()

            receiver.close()
            # First check if ready method returns False
            is_active = await optional_receiver.ready()
            assert is_active is False

            # Then check if `receive` method raises ReceiverStoppedError
            with pytest.raises(ReceiverStoppedError):
                await optional_receiver.receive()
