# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Tests for the LatestValueCache implementation."""

import asyncio

import pytest

from frequenz.channels import Broadcast
from frequenz.channels.experimental import GroupingLatestValueCache


@pytest.mark.integration
async def test_latest_value_cache_key() -> None:
    """Ensure LatestValueCache works with keys."""
    channel = Broadcast[tuple[int, str]](name="lvc_test")

    cache: GroupingLatestValueCache[int, tuple[int, str]] = GroupingLatestValueCache(
        channel.new_receiver(), key=lambda x: x[0]
    )
    sender = channel.new_sender()

    assert 5 not in cache
    assert cache.get(0) is None

    assert cache.keys() == set()

    await sender.send((5, "a"))
    await sender.send((6, "b"))
    await sender.send((5, "c"))
    await asyncio.sleep(0)

    assert 5 in cache
    assert 6 in cache
    assert 7 not in cache

    assert cache.get(5) == (5, "c")
    assert cache.get(6) == (6, "b")

    assert cache.keys() == {5, 6}

    assert cache.get(7, default=(7, "default")) == (7, "default")

    await sender.send((12, "d"))
    await asyncio.sleep(0)

    assert cache.get(12) == (12, "d")
    assert cache.get(12) == (12, "d")
    assert cache.get(5) == (5, "c")
    assert cache.get(6) == (6, "b")

    await sender.send((6, "e"))
    await sender.send((6, "f"))
    await sender.send((6, "g"))
    await asyncio.sleep(0)

    assert cache.get(6) == (6, "g")

    assert cache.keys() == {5, 6, 12}

    del cache[5]
    assert 5 not in cache
    assert 6 in cache

    assert cache.get(5) is None
    assert cache.keys() == {6, 12}
