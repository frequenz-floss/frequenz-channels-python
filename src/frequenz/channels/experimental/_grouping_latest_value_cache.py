# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""The GroupingLatestValueCache caches the latest values in a receiver grouped by key.

It provides a way to look up on demand, the latest value in a stream for any key, as
long as there has been at least one value received for that key.

[GroupingLatestValueCache][frequenz.channels.experimental.GroupingLatestValueCache]
takes a [Receiver][frequenz.channels.Receiver] and a `key` function as arguments and
stores the latest value received by that receiver for each key separately.

As soon as a value is received for a `key`, the
[`has_value`][frequenz.channels.experimental.GroupingLatestValueCache.has_value] method
returns `True` for that `key`, and the [`get`][frequenz.channels.LatestValueCache.get]
method for that `key` returns the latest value received.  The `get` method will raise an
exception if called before any messages have been received from the receiver for a given
`key`.

Example:
```python
from frequenz.channels import Broadcast
from frequenz.channels.experimental import GroupingLatestValueCache

channel = Broadcast[tuple[int, str]](name="lvc_test")

cache = GroupingLatestValueCache(channel.new_receiver(), key=lambda x: x[0])
sender = channel.new_sender()

assert not cache.has_value(6)

await sender.send((6, "twenty-six"))

assert cache.has_value(6)
assert cache.get(6) == (6, "twenty-six")
```
"""


import asyncio
import typing
from collections.abc import Set

from .._receiver import Receiver

T_co = typing.TypeVar("T_co", covariant=True)
HashableT = typing.TypeVar("HashableT", bound=typing.Hashable)


class GroupingLatestValueCache(typing.Generic[T_co, HashableT]):
    """A cache that stores the latest value in a receiver.

    It provides a way to look up the latest value in a stream without any delay,
    as long as there has been one value received.
    """

    def __init__(
        self,
        receiver: Receiver[T_co],
        key: typing.Callable[[T_co], typing.Any],
        *,
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
        self._receiver: Receiver[T_co] = receiver
        self._key: typing.Callable[[T_co], HashableT] = key
        self._unique_id: str = hex(id(self)) if unique_id is None else unique_id
        self._latest_value_by_key: dict[HashableT, T_co] = {}
        self._task: asyncio.Task[None] = asyncio.create_task(
            self._run(), name=f"LatestValueCache«{self._unique_id}»"
        )

    @property
    def unique_id(self) -> str:
        """The unique identifier of this instance."""
        return self._unique_id

    def keys(self) -> Set[HashableT]:
        """Return the set of keys for which values have been received.

        If no key function is provided, this will return an empty set.
        """
        return self._latest_value_by_key.keys()

    def get(self, key: HashableT) -> T_co:
        """Return the latest value that has been received.

        This raises a `ValueError` if no value has been received yet. Use `has_value` to
        check whether a value has been received yet, before trying to access the value,
        to avoid the exception.

        Args:
            key: An optional key to retrieve the latest value for that key. If not
                provided, it retrieves the latest value received overall.

        Returns:
            The latest value that has been received.

        Raises:
            ValueError: If no value has been received yet.
        """
        if key not in self._latest_value_by_key:
            raise ValueError(f"No value received for key: {key!r}")
        return self._latest_value_by_key[key]

    def has_value(self, key: HashableT) -> bool:
        """Check whether a value has been received yet.

        If `key` is provided, it checks whether a value has been received for that key.

        Args:
            key: An optional key to check if a value has been received for that key.

        Returns:
            `True` if a value has been received, `False` otherwise.
        """
        return key in self._latest_value_by_key

    def clear(self, key: HashableT) -> None:
        """Clear the latest value for a specific key.

        Args:
            key: The key for which to clear the latest value.
        """
        _ = self._latest_value_by_key.pop(key, None)

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
