# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A Channel receiver for watching for new (or modified) files."""

from __future__ import annotations

import asyncio
import pathlib
from collections import abc
from dataclasses import dataclass
from enum import Enum

from watchfiles import Change, awatch
from watchfiles.main import FileChange

from .._base_classes import Receiver
from .._exceptions import ReceiverStoppedError


class FileWatcher(Receiver["FileWatcher.Event"]):
    """A channel receiver that watches for file events."""

    class EventType(Enum):
        """Available types of changes to watch for."""

        CREATE = Change.added
        MODIFY = Change.modified
        DELETE = Change.deleted

    @dataclass(frozen=True)
    class Event:
        """A file change event."""

        type: FileWatcher.EventType
        """The type of change that was observed."""
        path: pathlib.Path
        """The path where the change was observed."""

    def __init__(
        self,
        paths: list[pathlib.Path | str],
        event_types: abc.Iterable[EventType] = frozenset(EventType),
    ) -> None:
        """Create a `FileWatcher` instance.

        Args:
            paths: Paths to watch for changes.
            event_types: Types of events to watch for. Defaults to watch for
                all event types.
        """
        self.event_types: frozenset[FileWatcher.EventType] = frozenset(event_types)
        self._stop_event = asyncio.Event()
        self._paths = [
            path if isinstance(path, pathlib.Path) else pathlib.Path(path)
            for path in paths
        ]
        self._awatch = awatch(
            *self._paths, stop_event=self._stop_event, watch_filter=self._filter_events
        )
        self._awatch_stopped_exc: Exception | None = None
        self._changes: set[FileChange] = set()

    def _filter_events(
        self,
        change: Change,
        path: str,  # pylint: disable=unused-argument
    ) -> bool:
        """Filter events based on the event type and path.

        Args:
            change: The type of change to be notified.
            path: The path of the file that changed.

        Returns:
            Whether the event should be notified.
        """
        return change in [event_type.value for event_type in self.event_types]

    def __del__(self) -> None:
        """Cleanup registered watches.

        `awatch` passes the `stop_event` to a separate task/thread. This way
        `awatch` getting destroyed properly. The background task will continue
        until the signal is received.
        """
        self._stop_event.set()

    async def ready(self) -> bool:
        """Wait until the receiver is ready with a value or an error.

        Once a call to `ready()` has finished, the value should be read with
        a call to `consume()` (`receive()` or iterated over). The receiver will
        remain ready (this method will return immediately) until it is
        consumed.

        Returns:
            Whether the receiver is still active.
        """
        # if there are messages waiting to be consumed, return immediately.
        if self._changes:
            return True

        # if it was already stopped, return immediately.
        if self._awatch_stopped_exc is not None:
            return False

        try:
            self._changes = await self._awatch.__anext__()
        except StopAsyncIteration as err:
            self._awatch_stopped_exc = err

        return True

    def consume(self) -> Event:
        """Return the latest event once `ready` is complete.

        Returns:
            The next event that was received.

        Raises:
            ReceiverStoppedError: if there is some problem with the receiver.
        """
        if not self._changes and self._awatch_stopped_exc is not None:
            raise ReceiverStoppedError(self) from self._awatch_stopped_exc

        assert self._changes, "`consume()` must be preceeded by a call to `ready()`"
        # Tuple of (Change, path) returned by watchfiles
        change, path_str = self._changes.pop()
        return FileWatcher.Event(
            type=FileWatcher.EventType(change), path=pathlib.Path(path_str)
        )
