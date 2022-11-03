# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A Channel receiver for watching for new (or modified) files."""
import asyncio
import pathlib
from enum import Enum
from typing import List, Optional, Set, Union

from watchfiles import Change, awatch

from frequenz.channels.base_classes import Receiver


class EventType(Enum):
    """Available types of changes to watch for."""

    CREATE = Change.added
    MODIFY = Change.modified
    DELETE = Change.deleted


class FileWatcher(Receiver[pathlib.Path]):
    """A channel receiver that watches for file events."""

    def __init__(
        self,
        paths: List[Union[pathlib.Path, str]],
        event_types: Optional[Set[EventType]] = None,
    ) -> None:
        """Create a `FileWatcher` instance.

        Args:
            paths: Paths to watch for changes.
            event_types: Types of events to watch for or `None` to watch for
                all event types.
        """
        if event_types is None:
            event_types = {EventType.CREATE, EventType.MODIFY, EventType.DELETE}

        self.event_types = event_types
        self._stop_event = asyncio.Event()
        self._paths = [
            path if isinstance(path, pathlib.Path) else pathlib.Path(path)
            for path in paths
        ]
        self._awatch = awatch(
            *self._paths,
            stop_event=self._stop_event,
            watch_filter=lambda change, path_str: (
                change in [event_type.value for event_type in event_types]  # type: ignore
                and pathlib.Path(path_str).is_file()
            ),
        )

    def __del__(self) -> None:
        """Cleanup registered watches.

        `awatch` passes the `stop_event` to a separate task/thread. This way
        `awatch` getting destroyed properly. The background task will continue
        until the signal is received.
        """
        self._stop_event.set()

    async def receive(self) -> Optional[pathlib.Path]:
        """Wait for the next file event and return its path.

        Returns:
            Path of next file.
        """
        while True:
            changes = await self._awatch.__anext__()
            for change in changes:
                # Tuple of (Change, path) returned by watchfiles
                if change is None or len(change) != 2:
                    return None

                _, path_str = change
                path = pathlib.Path(path_str)
                return path
