# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the `buffer_size` argument of broadcast channels."""

from typing import get_overloads

import pytest
from frequenz.core.warnings import asserting_no_deprecations

from frequenz.channels import BroadcastChannel, BroadcastReceiver, BroadcastSender


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
        BroadcastChannel[int]("test", False)  # type: ignore[call-overload]
    with pytest.raises(TypeError):
        # We want to test the runtime error.
        sender.subscribe("test", 5)  # type: ignore[call-overload]
    with pytest.raises(TypeError):
        # We want to test the runtime error.
        sender.subscribe("test", None, True)  # type: ignore[call-overload]


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


async def test_limit_keyword_is_deprecated() -> None:
    """Ensure passing `limit` by keyword warns, but still sets the buffer size."""
    with pytest.deprecated_call(
        match=r"^The argument limit in frequenz\.channels\.BroadcastChannel is deprecated\b"
    ) as warnings_record:
        sender, receiver_1 = BroadcastChannel[int](
            name="test", limit=2, warn_on_overflow=False
        )
    assert warnings_record[0].filename == __file__

    with pytest.deprecated_call(
        match=(
            r"^The argument limit in frequenz\.channels\.BroadcastSender\.subscribe "
            r"is deprecated\b"
        )
    ) as warnings_record:
        receiver_2 = sender.subscribe(limit=3, warn_on_overflow=False)
    assert warnings_record[0].filename == __file__

    for message in range(5):
        await sender.send(message)

    assert _drain(receiver_1) == [3, 4]
    assert _drain(receiver_2) == [2, 3, 4]


@pytest.mark.parametrize("limit", [0, -1])
async def test_limit_must_be_positive(limit: int) -> None:
    """Ensure the error of a deprecated `limit` smaller than 1 names `limit`."""
    with pytest.deprecated_call():
        with pytest.raises(ValueError, match="limit must be at least 1"):
            _ = BroadcastChannel[int](name="test", limit=limit)

    sender, _receiver = BroadcastChannel[int](name="test")
    with pytest.deprecated_call():
        with pytest.raises(ValueError, match="limit must be at least 1"):
            _ = sender.subscribe(limit=limit)


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


async def test_limit_and_buffer_size_conflict_does_not_warn() -> None:
    """Ensure the error for passing both arguments comes without a warning."""
    with asserting_no_deprecations():
        with pytest.raises(TypeError):
            # We want to test the runtime error.
            BroadcastChannel[int](  # type: ignore[call-overload]
                name="test", limit=2, buffer_size=2
            )


def test_deprecated_overloads_have_the_runtime_message() -> None:
    """Ensure `mypy` and the runtime report the same message for `limit`."""
    for function, name in (
        (BroadcastChannel.__new__, "BroadcastChannel"),
        (BroadcastSender.subscribe, "BroadcastSender.subscribe"),
    ):
        deprecated_overloads = [
            message
            for overload in get_overloads(function)
            if (message := getattr(overload, "__deprecated__", None)) is not None
        ]
        assert deprecated_overloads == [
            f"The argument limit in frequenz.channels.{name} is deprecated and will "
            "be removed in v2.0.0. Use buffer_size instead."
        ]
