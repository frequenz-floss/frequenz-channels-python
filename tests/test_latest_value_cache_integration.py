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
