# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the `buffer_size` argument of broadcast channels."""

import pytest

from frequenz.channels import BroadcastChannel, BroadcastReceiver


def _drain(receiver: BroadcastReceiver[int]) -> list[int]:
    """Return all messages in a receiver's buffer, oldest first."""
    messages = []
    while len(receiver) > 0:
        messages.append(receiver.consume())
    return messages


async def test_channel_buffer_size() -> None:
    """Ensure `BroadcastChannel()` uses `buffer_size` for the initial receiver."""
    sender, receiver = BroadcastChannel[int](
        name="test", buffer_size=2, warn_on_overflow=False
    )

    for message in range(5):
        await sender.send(message)

    assert _drain(receiver) == [3, 4]


async def test_subscribe_buffer_size() -> None:
    """Ensure `subscribe()` uses `buffer_size` for the new receiver."""
    sender, _receiver = BroadcastChannel[int](name="test")
    receiver = sender.subscribe(buffer_size=2, warn_on_overflow=False)

    for message in range(5):
        await sender.send(message)

    assert _drain(receiver) == [3, 4]


async def test_default_buffer_size() -> None:
    """Ensure both buffers default to 50 messages."""
    sender, receiver_1 = BroadcastChannel[int](name="test", warn_on_overflow=False)
    receiver_2 = sender.subscribe(warn_on_overflow=False)

    for message in range(60):
        await sender.send(message)

    assert _drain(receiver_1) == list(range(10, 60))
    assert _drain(receiver_2) == list(range(10, 60))


async def test_buffer_size_is_keyword_only() -> None:
    """Ensure `buffer_size` can't be passed by position."""
    sender, _receiver = BroadcastChannel[int](name="test")

    with pytest.raises(TypeError):
        # We want to test the runtime error.
        # pylint: disable-next=too-many-function-args
        BroadcastChannel[int]("test", False, 5, True, 7)  # type: ignore[call-overload]
    with pytest.raises(TypeError):
        # We want to test the runtime error.
        sender.subscribe("test", 5, True, 7)  # type: ignore[call-overload]


@pytest.mark.parametrize("buffer_size", [0, -1])
async def test_buffer_size_must_be_positive(buffer_size: int) -> None:
    """Ensure the error of a buffer smaller than 1 names `buffer_size`."""
    with pytest.raises(ValueError, match="buffer_size must be at least 1"):
        _ = BroadcastChannel[int](name="test", buffer_size=buffer_size)

    sender, _receiver = BroadcastChannel[int](name="test")
    with pytest.raises(ValueError, match="buffer_size must be at least 1"):
        _ = sender.subscribe(buffer_size=buffer_size)


async def test_limit_and_buffer_size_conflict() -> None:
    """Ensure passing both `limit` and `buffer_size` raises a `TypeError`."""
    with pytest.raises(TypeError, match="both `limit` and `buffer_size`"):
        # We want to test the runtime error.
        BroadcastChannel[int](name="test", limit=2, buffer_size=2)  # type: ignore[call-overload]

    sender, _receiver = BroadcastChannel[int](name="test")
    with pytest.raises(TypeError, match="both `limit` and `buffer_size`"):
        # We want to test the runtime error.
        sender.subscribe(limit=2, buffer_size=2)  # type: ignore[call-overload]
