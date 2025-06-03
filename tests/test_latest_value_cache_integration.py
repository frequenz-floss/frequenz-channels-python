# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Tests for the LatestValueCache implementation."""

import asyncio

import pytest

from frequenz.channels import Broadcast, LatestValueCache


@pytest.mark.integration
async def test_latest_value_cache() -> None:
    """Ensure LatestValueCache always gives out the latest value."""
    channel = Broadcast[int](name="lvc_test")

    cache = LatestValueCache(channel.new_receiver())
    sender = channel.new_sender()

    assert not cache.has_value()
    with pytest.raises(ValueError, match="No value has been received yet."):
        cache.get()

    await sender.send(5)
    await sender.send(6)
    await asyncio.sleep(0)

    assert cache.has_value()
    assert cache.get() == 6
    assert cache.get() == 6

    await sender.send(12)
    await asyncio.sleep(0)

    assert cache.get() == 12
    assert cache.get() == 12
    assert cache.get() == 12

    await sender.send(15)
    await sender.send(18)
    await sender.send(19)
    await asyncio.sleep(0)

    assert cache.get() == 19


@pytest.mark.integration
async def test_latest_value_cache_key() -> None:
    """Ensure LatestValueCache works with keys."""
    channel = Broadcast[tuple[int, str]](name="lvc_test")

    cache = LatestValueCache(channel.new_receiver(), key=lambda x: x[0])
    sender = channel.new_sender()

    assert not cache.has_value()
    with pytest.raises(ValueError, match="No value has been received yet."):
        cache.get()
    with pytest.raises(ValueError, match="No value received for key: 0"):
        cache.get(0)

    await sender.send((5, "a"))
    await sender.send((6, "b"))
    await sender.send((5, "c"))
    await asyncio.sleep(0)

    assert cache.has_value()
    assert cache.has_value(5)
    assert cache.has_value(6)
    assert not cache.has_value(7)

    assert cache.get() == (5, "c")
    assert cache.get(5) == (5, "c")
    assert cache.get(6) == (6, "b")

    with pytest.raises(ValueError, match="No value received for key: 7"):
        cache.get(7)

    await sender.send((12, "d"))
    await asyncio.sleep(0)

    assert cache.get() == (12, "d")
    assert cache.get() == (12, "d")
    assert cache.get(12) == (12, "d")
    assert cache.get(12) == (12, "d")
    assert cache.get(5) == (5, "c")
    assert cache.get(6) == (6, "b")

    await sender.send((6, "e"))
    await sender.send((6, "f"))
    await sender.send((6, "g"))
    await asyncio.sleep(0)

    assert cache.get(6) == (6, "g")
