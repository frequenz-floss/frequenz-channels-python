# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""The LatestValueCache caches the latest value in a receiver.

It provides a way to look up the latest value in a stream whenever required, as
long as there has been one value received.

[LatestValueCache][frequenz.channels.LatestValueCache] takes a
[Receiver][frequenz.channels.Receiver] as an argument and stores the latest
value received by that receiver.  It also takes an optional `key` function
that allows you to group the values by a specific key.  If the `key` is
provided, the cache will store the latest value for each key separately,
otherwise it will store only the latest value received overall.

As soon as a value is received, its
[`has_value`][frequenz.channels.LatestValueCache.has_value] method returns
`True`, and its [`get`][frequenz.channels.LatestValueCache.get] method returns
the latest value received.  The `get` method will raise an exception if called
before any messages have been received from the receiver.

Both `has_value` and `get` methods can take an optional `key` argument to
check or retrieve the latest value for that specific key.

Example:
```python
from frequenz.channels import Broadcast, LatestValueCache

channel = Broadcast[int](name="lvc_test")

cache = LatestValueCache(channel.new_receiver())
sender = channel.new_sender()

assert not cache.has_value()

await sender.send(5)

assert cache.has_value()
assert cache.get() == 5
```
"""

from __future__ import annotations

import asyncio
import typing

from ._receiver import Receiver

T_co = typing.TypeVar("T_co", covariant=True)
HashableT = typing.TypeVar("HashableT", bound=typing.Hashable)


class Sentinel:
    """A sentinel to denote that no value has been received yet."""

    def __init__(self, desc: str) -> None:
        """Initialize the sentinel."""
        self._desc = desc

    def __str__(self) -> str:
        """Return a string representation of this sentinel."""
        return f"<Sentinel: {self._desc}>"


NO_KEY: typing.Final[Sentinel] = Sentinel("no key provided")
NO_KEY_FUNCTION: typing.Final[Sentinel] = Sentinel("no key function provided")
NO_VALUE_RECEIVED: typing.Final[Sentinel] = Sentinel("no value received yet")


class LatestValueCache(typing.Generic[T_co, HashableT]):
    """A cache that stores the latest value in a receiver.

    It provides a way to look up the latest value in a stream without any delay,
    as long as there has been one value received.
    """

    @typing.overload
    def __init__(
        self: LatestValueCache[T_co, Sentinel],
        receiver: Receiver[T_co],
        *,
        unique_id: str | None = None,
        key: Sentinel = NO_KEY_FUNCTION,
    ) -> None:
        """Create a new cache that does not use keys.

        Args:
            receiver: The receiver to cache.
            unique_id: A string to help uniquely identify this instance. If not
                provided, a unique identifier will be generated from the object's
                [`id()`][id]. It is used mostly for debugging purposes.
            key: This parameter is ignored when set to `None`.
        """

    @typing.overload
    def __init__(
        self: LatestValueCache[T_co, HashableT],
        receiver: Receiver[T_co],
        *,
        unique_id: str | None = None,
        key: typing.Callable[[T_co], HashableT],
    ) -> None:
        """Create a new cache that uses keys.

        Args:
            receiver: The receiver to cache.
            unique_id: A string to help uniquely identify this instance. If not
                provided, a unique identifier will be generated from the object's
                [`id()`][id]. It is used mostly for debugging purposes.
            key: A function that takes a value and returns a key to group the values by.
                If provided, the cache will store the latest value for each key separately.
        """

    def __init__(
        self,
        receiver: Receiver[T_co],
        *,
        unique_id: str | None = None,
        key: typing.Callable[[T_co], typing.Any] | Sentinel = NO_KEY_FUNCTION,
    ) -> None:
        """Create a new cache.

        Args:
            receiver: The receiver to cache.
            unique_id: A string to help uniquely identify this instance. If not
                provided, a unique identifier will be generated from the object's
                [`id()`][id]. It is used mostly for debugging purposes.
            key: An optional function that takes a value and returns a key to group the
                values by. If provided, the cache will store the latest value for each
                key separately. If not provided, it will store only the latest value
                received overall.
        """
        self._receiver = receiver
        self._key: typing.Callable[[T_co], HashableT] | Sentinel = key
        self._unique_id: str = hex(id(self)) if unique_id is None else unique_id
        self._latest_value: T_co | Sentinel = NO_VALUE_RECEIVED
        self._latest_value_by_key: dict[HashableT, T_co] = {}
        self._task = asyncio.create_task(
            self._run(), name=f"LatestValueCache«{self._unique_id}»"
        )

    @property
    def unique_id(self) -> str:
        """The unique identifier of this instance."""
        return self._unique_id

    def get(self, key: HashableT | Sentinel = NO_KEY) -> T_co:
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
        if not isinstance(key, Sentinel):
            if key not in self._latest_value_by_key:
                raise ValueError(f"No value received for key: {key!r}")
            return self._latest_value_by_key[key]

        if isinstance(self._latest_value, Sentinel):
            raise ValueError("No value has been received yet.")
        return self._latest_value

    def has_value(self, key: HashableT | Sentinel = NO_KEY) -> bool:
        """Check whether a value has been received yet.

        If `key` is provided, it checks whether a value has been received for that key.

        Args:
            key: An optional key to check if a value has been received for that key.

        Returns:
            `True` if a value has been received, `False` otherwise.
        """
        if not isinstance(key, Sentinel):
            return key in self._latest_value_by_key
        return not isinstance(self._latest_value, Sentinel)

    async def _run(self) -> None:
        async for value in self._receiver:
            self._latest_value = value
            if not isinstance(self._key, Sentinel):
                key = self._key(value)
                self._latest_value_by_key[key] = value

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
            f"<LatestValueCache latest_value={self._latest_value!r}, "
            f"receiver={self._receiver!r}, unique_id={self._unique_id!r}>"
        )

    def __str__(self) -> str:
        """Return the last value seen by this cache."""
        return str(self._latest_value)
