# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the `buffer_size` argument of broadcast channels."""

import pytest
from frequenz.core.warnings import asserting_no_deprecations

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


async def test_options_are_keyword_only() -> None:
    """Ensure every option but the name has to be passed by keyword."""
    sender, _receiver = BroadcastChannel[int](name="test")

    with pytest.raises(TypeError):
        # We want to test the runtime error.
        # pylint: disable-next=too-many-function-args
        BroadcastChannel[int]("test", False)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        # We want to test the runtime error.
        sender.subscribe("test", 5)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        # We want to test the runtime error.
        sender.subscribe("test", None, True)  # type: ignore[call-arg]


async def test_subscribe_none_uses_the_channel_options() -> None:
    """Ensure passing `None` to `subscribe()` is the same as not passing it."""
    sender, _receiver = BroadcastChannel[int](
        name="test", buffer_size=2, warn_on_overflow=False
    )
    receiver = sender.subscribe(buffer_size=None, warn_on_overflow=None)

    for message in range(5):
        await sender.send(message)

    assert _drain(receiver) == [3, 4]
    assert not receiver._warn_on_overflow  # pylint: disable=protected-access


async def test_receiver_repr_shows_buffer_size() -> None:
    """Ensure the receiver's `repr()` shows its buffer size as `buffer_size`."""
    _sender, receiver = BroadcastChannel[int](name="test", buffer_size=2)

    assert "buffer_size=2" in repr(receiver)
    assert "limit" not in repr(receiver)


@pytest.mark.parametrize("buffer_size", [0, -1])
async def test_buffer_size_must_be_positive(buffer_size: int) -> None:
    """Ensure the error of a buffer smaller than 1 names `buffer_size`."""
    with pytest.raises(ValueError, match="buffer_size must be at least 1"):
        _ = BroadcastChannel[int](name="test", buffer_size=buffer_size)

    sender, _receiver = BroadcastChannel[int](name="test")
    with pytest.raises(ValueError, match="buffer_size must be at least 1"):
        _ = sender.subscribe(buffer_size=buffer_size)


async def test_limit_is_removed() -> None:
    """Ensure the removed `limit` argument raises a `TypeError`."""
    with pytest.raises(TypeError):
        # We want to test the runtime error.
        # pylint: disable-next=unexpected-keyword-arg
        BroadcastChannel[int](name="test", limit=2)  # type: ignore[call-arg]

    sender, _receiver = BroadcastChannel[int](name="test")
    with pytest.raises(TypeError):
        # We want to test the runtime error.
        sender.subscribe(limit=2)  # type: ignore[call-arg]


async def test_buffer_size_is_not_deprecated() -> None:
    """Ensure the new argument and the defaults don't warn."""
    with asserting_no_deprecations():
        sender, _receiver = BroadcastChannel[int](
            name="test", buffer_size=2, warn_on_overflow=False
        )
        _ = sender.subscribe(buffer_size=2, warn_on_overflow=False)
        _ = sender.subscribe()
        _ = sender.subscribe("name")
        _ = BroadcastChannel[int]("name", resend_latest=True)
