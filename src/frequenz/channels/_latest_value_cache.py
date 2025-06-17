# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""The LatestValueCache caches the latest value in a receiver.

It provides a way to look up the latest value in a stream whenever required, as
long as there has been one value received.

[LatestValueCache][frequenz.channels.LatestValueCache] takes a
[Receiver][frequenz.channels.Receiver] as an argument and stores the latest
value received by that receiver.  As soon as a value is received, its
[`has_value`][frequenz.channels.LatestValueCache.has_value] method returns
`True`, and its [`get`][frequenz.channels.LatestValueCache.get] method returns
the latest value received.  The `get` method will raise an exception if called
before any messages have been received from the receiver.

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

import asyncio
import typing

from ._receiver import Receiver

T_co = typing.TypeVar("T_co", covariant=True)


class _Sentinel:
    """A sentinel to denote that no value has been received yet."""

    def __str__(self) -> str:
        """Return a string representation of this sentinel."""
        return "<no value received yet>"


class LatestValueCache(typing.Generic[T_co]):
    """A cache that stores the latest value in a receiver.

    It provides a way to look up the latest value in a stream without any delay,
    as long as there has been one value received.
    """

    def __init__(
        self, receiver: Receiver[T_co], *, unique_id: str | None = None
    ) -> None:
        """Create a new cache.

        Args:
            receiver: The receiver to cache.
            unique_id: A string to help uniquely identify this instance. If not
                provided, a unique identifier will be generated from the object's
                [`id()`][id]. It is used mostly for debugging purposes.
        """
        self._receiver = receiver
        self._unique_id: str = hex(id(self)) if unique_id is None else unique_id
        self._latest_value: T_co | _Sentinel = _Sentinel()
        self._task = asyncio.create_task(
            self._run(), name=f"LatestValueCache«{self._unique_id}»"
        )

    @property
    def unique_id(self) -> str:
        """The unique identifier of this instance."""
        return self._unique_id

    def get(self) -> T_co:
        """Return the latest value that has been received.

        This raises a `ValueError` if no value has been received yet. Use `has_value` to
        check whether a value has been received yet, before trying to access the value,
        to avoid the exception.

        Returns:
            The latest value that has been received.

        Raises:
            ValueError: If no value has been received yet.
        """
        if isinstance(self._latest_value, _Sentinel):
            raise ValueError("No value has been received yet.")
        return self._latest_value

    def has_value(self) -> bool:
        """Check whether a value has been received yet.

        Returns:
            `True` if a value has been received, `False` otherwise.
        """
        return not isinstance(self._latest_value, _Sentinel)

    async def _run(self) -> None:
        async for value in self._receiver:
            self._latest_value = value

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
