# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""A receiver that can be made ready through an event."""


import asyncio as _asyncio

from frequenz.channels import _base_classes, _exceptions


class Event(_base_classes.Receiver[None]):
    """A receiver that can be made ready through an event.

    The receiver (the [`ready()`][frequenz.channels.util.Event.ready] method) will wait
    until [`set()`][frequenz.channels.util.Event.set] is called.  At that point the
    receiver will wait again after the event is
    [`consume()`][frequenz.channels.Receiver.consume]d.

    The receiver can be completely stopped by calling
    [`stop()`][frequenz.channels.util.Event.stop].

    Example:
        ```python
        import asyncio
        from frequenz.channels import Receiver
        from frequenz.channels.util import Event, select, selected_from

        other_receiver: Receiver[int] = ...
        exit_event = Event()

        async def exit_after_10_seconds() -> None:
            asyncio.sleep(10)
            exit_event.set()

        asyncio.ensure_future(exit_after_10_seconds())

        async for selected in select(exit_event, other_receiver):
            if selected_from(selected, exit_event):
                break
            if selected_from(selected, other_receiver):
                print(selected.value)
            else:
                assert False, "Unknown receiver selected"
        ```
    """

    def __init__(self, name: str | None = None) -> None:
        """Create a new instance.

        Args:
            name: The name of the receiver.  If `None` the `id(self)` will be used as
                the name.  This is only for debugging purposes, it will be shown in the
                string representation of the receiver.
        """
        self._event: _asyncio.Event = _asyncio.Event()
        """The event that is set when the receiver is ready."""

        self._name: str = name or str(id(self))
        """The name of the receiver.

        This is for debugging purposes, it will be shown in the string representation
        of the receiver.
        """

        self._is_set: bool = False
        """Whether the receiver is ready to be consumed.

        This is used to differentiate between when the receiver was stopped (the event
        is triggered too) but still there is an event to be consumed and when it was
        stopped but was not explicitly set().
        """

        self._is_stopped: bool = False
        """Whether the receiver is stopped."""

    @property
    def name(self) -> str:
        """The name of this receiver.

        This is for debugging purposes, it will be shown in the string representation
        of this receiver.

        Returns:
            The name of this receiver.
        """
        return self._name

    @property
    def is_set(self) -> bool:
        """Whether this receiver is set (ready).

        Returns:
            Whether this receiver is set (ready).
        """
        return self._is_set

    @property
    def is_stopped(self) -> bool:
        """Whether this receiver is stopped.

        Returns:
            Whether this receiver is stopped.
        """
        return self._is_stopped

    def stop(self) -> None:
        """Stop this receiver."""
        self._is_stopped = True
        self._event.set()

    def set(self) -> None:
        """Trigger the event (make the receiver ready)."""
        self._is_set = True
        self._event.set()

    async def ready(self) -> bool:
        """Wait until this receiver is ready.

        Returns:
            Whether this receiver is still running.
        """
        if self._is_stopped:
            return False
        await self._event.wait()
        return not self._is_stopped

    def consume(self) -> None:
        """Consume the event.

        This makes this receiver wait again until the event is set again.

        Raises:
            ReceiverStoppedError: If this receiver is stopped.
        """
        if not self._is_set and self._is_stopped:
            raise _exceptions.ReceiverStoppedError(self)

        assert self._is_set, "calls to `consume()` must be follow a call to `ready()`"

        self._is_set = False
        self._event.clear()

    def __str__(self) -> str:
        """Return a string representation of this receiver.

        Returns:
            A string representation of this receiver.
        """
        return f"{type(self).__name__}({self._name!r})"

    def __repr__(self) -> str:
        """Return a string representation of this receiver.

        Returns:
            A string representation of this receiver.
        """
        return (
            f"<{type(self).__name__} name={self._name!r} is_set={self.is_set!r} "
            f"is_stopped={self.is_stopped!r}>"
        )
