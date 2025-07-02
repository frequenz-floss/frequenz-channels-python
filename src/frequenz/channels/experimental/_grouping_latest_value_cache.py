# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""The GroupingLatestValueCache caches the latest values in a receiver grouped by key."""


import asyncio
from collections.abc import (
    Callable,
    Hashable,
    ItemsView,
    Iterator,
    KeysView,
    Mapping,
    ValuesView,
)
from typing import TypeVar, overload

from typing_extensions import override

from .._receiver import Receiver

ValueT_co = TypeVar("ValueT_co", covariant=True)
"""Covariant type variable for the values cached by the `GroupingLatestValueCache`."""

DefaultT = TypeVar("DefaultT")
"""Type variable for the default value returned by `GroupingLatestValueCache.get`."""

HashableT = TypeVar("HashableT", bound=Hashable)
"""Type variable for the keys used to group values in the `GroupingLatestValueCache`."""


class _NotSpecified:
    """A sentinel value to indicate that no default value was provided."""

    def __repr__(self) -> str:
        """Return a string representation of this sentinel."""
        return "<_NotSpecified>"


class GroupingLatestValueCache(Mapping[HashableT, ValueT_co]):
    """A cache that stores the latest value in a receiver, grouped by key.

    It provides a way to look up on demand, the latest value in a stream for any key, as
    long as there has been at least one value received for that key.

    [GroupingLatestValueCache][frequenz.channels.experimental.GroupingLatestValueCache]
    takes a [Receiver][frequenz.channels.Receiver] and a `key` function as arguments and
    stores the latest value received by that receiver for each key separately.

    The `GroupingLatestValueCache` implements the [`Mapping`][collections.abc.Mapping]
    interface, so it can be used like a dictionary.  Additionally other methods from
    [`MutableMapping`][collections.abc.MutableMapping] are implemented, but only
    methods removing items from the cache are allowed, such as
    [`pop()`][frequenz.channels.experimental.GroupingLatestValueCache.pop],
    [`popitem()`][frequenz.channels.experimental.GroupingLatestValueCache.popitem],
    [`clear()`][frequenz.channels.experimental.GroupingLatestValueCache.clear], and
    [`__delitem__()`][frequenz.channels.experimental.GroupingLatestValueCache.__delitem__].
    Other update methods are not provided because the user should not update the
    cache values directly.

    Example:
        ```python
        from frequenz.channels import Broadcast
        from frequenz.channels.experimental import GroupingLatestValueCache

        channel = Broadcast[tuple[int, str]](name="lvc_test")

        cache = GroupingLatestValueCache(channel.new_receiver(), key=lambda x: x[0])
        sender = channel.new_sender()

        assert cache.get(6) is None
        assert 6 not in cache

        await sender.send((6, "twenty-six"))

        assert 6 in cache
        assert cache.get(6) == (6, "twenty-six")

        del cache[6]

        assert cache.get(6) is None
        assert 6 not in cache

        await cache.stop()
        ```
    """

    def __init__(
        self,
        receiver: Receiver[ValueT_co],
        *,
        key: Callable[[ValueT_co], HashableT],
        unique_id: str | None = None,
    ) -> None:
        """Create a new cache.

        Args:
            receiver: The receiver to cache values from.
            key: An function that takes a value and returns a key to group the values
                by.
            unique_id: A string to help uniquely identify this instance. If not
                provided, a unique identifier will be generated from the object's
                [`id()`][id]. It is used mostly for debugging purposes.
        """
        self._receiver: Receiver[ValueT_co] = receiver
        self._key: Callable[[ValueT_co], HashableT] = key
        self._unique_id: str = hex(id(self)) if unique_id is None else unique_id
        self._latest_value_by_key: dict[HashableT, ValueT_co] = {}
        self._task: asyncio.Task[None] = asyncio.create_task(
            self._run(), name=f"LatestValueCache«{self._unique_id}»"
        )

    @property
    def unique_id(self) -> str:
        """The unique identifier of this instance."""
        return self._unique_id

    @override
    def keys(self) -> KeysView[HashableT]:
        """Return the set of keys for which values have been received.

        If no key function is provided, this will return an empty set.
        """
        return self._latest_value_by_key.keys()

    @override
    def items(self) -> ItemsView[HashableT, ValueT_co]:
        """Return an iterator over the key-value pairs of the latest values received."""
        return self._latest_value_by_key.items()

    @override
    def values(self) -> ValuesView[ValueT_co]:
        """Return an iterator over the latest values received."""
        return self._latest_value_by_key.values()

    @overload
    def get(self, key: HashableT, default: None = None) -> ValueT_co | None:
        """Return the latest value that has been received for a specific key."""

    # MyPy passes this overload as a valid signature, but pylint does not like it.
    @overload
    def get(  # pylint: disable=signature-differs
        self, key: HashableT, default: DefaultT
    ) -> ValueT_co | DefaultT:
        """Return the latest value that has been received for a specific key."""

    @override
    def get(
        self, key: HashableT, default: DefaultT | None = None
    ) -> ValueT_co | DefaultT | None:
        """Return the latest value that has been received.

        Args:
            key: An optional key to retrieve the latest value for that key. If not
                provided, it retrieves the latest value received overall.
            default: The default value to return if no value has been received yet for
                the specified key. If not provided, it defaults to `None`.

        Returns:
            The latest value that has been received.
        """
        return self._latest_value_by_key.get(key, default)

    @override
    def __iter__(self) -> Iterator[HashableT]:
        """Return an iterator over the keys for which values have been received."""
        return iter(self._latest_value_by_key)

    @override
    def __len__(self) -> int:
        """Return the number of keys for which values have been received."""
        return len(self._latest_value_by_key)

    @override
    def __getitem__(self, key: HashableT) -> ValueT_co:
        """Return the latest value that has been received for a specific key.

        Args:
            key: The key to retrieve the latest value for.

        Returns:
            The latest value that has been received for that key.
        """
        return self._latest_value_by_key[key]

    @override
    def __contains__(self, key: object, /) -> bool:
        """Check if a value has been received for a specific key.

        Args:
            key: The key to check for.

        Returns:
            `True` if a value has been received for that key, `False` otherwise.
        """
        return key in self._latest_value_by_key

    @override
    def __eq__(self, other: object, /) -> bool:
        """Check if this cache is equal to another object.

        Two caches are considered equal if they have the same keys and values.

        Args:
            other: The object to compare with.

        Returns:
            `True` if the caches are equal, `False` otherwise.
        """
        match other:
            case GroupingLatestValueCache():
                return self._latest_value_by_key == other._latest_value_by_key
            case Mapping():
                return self._latest_value_by_key == other
            case _:
                return NotImplemented

    @override
    def __ne__(self, value: object, /) -> bool:
        """Check if this cache is not equal to another object.

        Args:
            value: The object to compare with.

        Returns:
            `True` if the caches are not equal, `False` otherwise.
        """
        return not self.__eq__(value)

    def __delitem__(self, key: HashableT) -> None:
        """Clear the latest value for a specific key.

        Args:
            key: The key for which to clear the latest value.
        """
        del self._latest_value_by_key[key]

    @overload
    def pop(self, key: HashableT, /) -> ValueT_co | None:
        """Remove the latest value for a specific key and return it."""

    @overload
    def pop(self, key: HashableT, /, default: DefaultT) -> ValueT_co | DefaultT:
        """Remove the latest value for a specific key and return it."""

    def pop(
        self, key: HashableT, /, default: DefaultT | _NotSpecified = _NotSpecified()
    ) -> ValueT_co | DefaultT | None:
        """Remove the latest value for a specific key and return it.

        If no value has been received yet for that key, it returns the default value or
        raises a `KeyError` if no default value is provided.

        Args:
            key: The key for which to remove the latest value.
            default: The default value to return if no value has been received yet for
                the specified key.

        Returns:
            The latest value that has been received for that key, or the default value if
                no value has been received yet and a default value is provided.
        """
        if isinstance(default, _NotSpecified):
            return self._latest_value_by_key.pop(key)
        return self._latest_value_by_key.pop(key, default)

    def popitem(self) -> tuple[HashableT, ValueT_co]:
        """Remove and return a (key, value) pair from the cache.

        Pairs are returned in LIFO (last-in, first-out) order.

        Returns:
            A tuple containing the key and the latest value that has been received for
                that key.
        """
        return self._latest_value_by_key.popitem()

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._latest_value_by_key.clear()

    async def stop(self) -> None:
        """Stop the cache."""
        if not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def __repr__(self) -> str:
        """Return a string representation of this cache."""
        return (
            f"<GroupingLatestValueCache num_keys={len(self._latest_value_by_key.keys())}, "
            f"receiver={self._receiver!r}, unique_id={self._unique_id!r}>"
        )

    async def _run(self) -> None:
        async for value in self._receiver:
            key = self._key(value)
            self._latest_value_by_key[key] = value
