# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Tests for the LatestValueCache implementation."""

import asyncio
import importlib

import pytest

from frequenz.channels import Broadcast
from frequenz.channels.experimental import GroupingLatestValueCache

# These tests use the deprecated Broadcast on purpose.
pytestmark = pytest.mark.filterwarnings("once::DeprecationWarning")


@pytest.mark.integration
async def test_latest_value_cache_key() -> None:  # pylint: disable=too-many-statements
    """Ensure LatestValueCache works with keys."""
    channel = Broadcast[tuple[int, str]](name="lvc_test")

    with pytest.deprecated_call():
        cache: GroupingLatestValueCache[int, tuple[int, str]] = (
            GroupingLatestValueCache(channel.new_receiver(), key=lambda x: x[0])
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
    assert cache[5] == (5, "c")
    assert cache.get(6) == (6, "b")
    assert cache[6] == (6, "b")

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

    assert cache.pop(6) == (6, "g")
    assert 6 not in cache
    assert cache.keys() == {12}

    assert cache.pop(8, default=True) is True
    with pytest.raises(KeyError):
        cache.pop(8)

    assert cache.popitem() == (12, (12, "d"))
    assert 12 not in cache
    assert not cache

    await sender.send((1, "h"))
    await sender.send((2, "i"))
    await asyncio.sleep(0)

    expected = {1: (1, "h"), 2: (2, "i")}
    assert cache.keys() == expected.keys()
    assert list(cache.values()) == list(expected.values())
    assert list(cache.items()) == list(expected.items())
    assert cache == expected
    assert list(cache) == list(expected)

    cache.clear()
    assert not cache
    assert cache.keys() == set()

    await cache.stop()


@pytest.mark.integration
async def test_equality() -> None:
    """Test that two caches with the same content are equal."""
    channel = Broadcast[tuple[int, str]](name="lvc_test")

    with pytest.deprecated_call():
        cache1: GroupingLatestValueCache[int, tuple[int, str]] = (
            GroupingLatestValueCache(channel.new_receiver(), key=lambda x: x[0])
        )
    with pytest.deprecated_call():
        cache2: GroupingLatestValueCache[int, tuple[int, str]] = (
            GroupingLatestValueCache(channel.new_receiver(), key=lambda x: x[0])
        )

    sender = channel.new_sender()
    await sender.send((1, "one"))
    await sender.send((2, "two"))
    await asyncio.sleep(0)

    assert cache1 == cache2

    del cache1[1]
    assert cache1 != cache2

    await cache1.stop()
    await cache2.stop()


@pytest.mark.integration
async def test_grouping_latest_value_cache_is_deprecated() -> None:
    """Test that creating a GroupingLatestValueCache warns."""
    channel = Broadcast[int](name="lvc_test")
    with pytest.deprecated_call(
        match=r"^frequenz\.channels\.experimental\.GroupingLatestValueCache is "
        r"deprecated and will be removed in v2\.0\.0\. Copy its code into your project"
    ):
        cache = GroupingLatestValueCache(channel.new_receiver(), key=lambda x: x)
    await cache.stop()


@pytest.mark.parametrize("name", ["DefaultT", "HashableT", "ValueT_co"])
def test_type_variables_are_deprecated(name: str) -> None:
    """Test that reaching the type variables of GroupingLatestValueCache warns."""
    experimental = importlib.import_module("frequenz.channels.experimental")
    private = importlib.import_module(
        "frequenz.channels.experimental._grouping_latest_value_cache"
    )
    with pytest.deprecated_call(
        match=rf"^frequenz\.channels\.experimental\.{name} is deprecated and will be "
        r"removed in v2\.0\.0, together with "
        r"frequenz\.channels\.experimental\.GroupingLatestValueCache\."
    ):
        value = getattr(experimental, name)
    assert value is getattr(private, name)
