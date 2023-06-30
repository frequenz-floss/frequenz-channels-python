# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Channel utilities.

A module with several utilities to work with channels:

* [Event][frequenz.channels.util.Event]:
  A [receiver][frequenz.channels.Receiver] that can be made ready through an event.

* [FileWatcher][frequenz.channels.util.FileWatcher]:
  A [receiver][frequenz.channels.Receiver] that watches for file events.

* [Merge][frequenz.channels.util.Merge]:
  A [receiver][frequenz.channels.Receiver] that merge messages coming from
  multiple receivers into a single stream.

* [MergeNamed][frequenz.channels.util.MergeNamed]:
  A [receiver][frequenz.channels.Receiver] that merge messages coming from
  multiple receivers into a single named stream, allowing to identify the
  origin of each message.

* [Timer][frequenz.channels.util.Timer]:
  A [receiver][frequenz.channels.Receiver] that ticks at certain intervals.

* [select][frequenz.channels.util.select]:  Iterate over the values of all
  [receivers][frequenz.channels.Receiver] as new values become available.
"""

from ._event import Event
from ._file_watcher import FileWatcher
from ._merge import Merge
from ._merge_named import MergeNamed
from ._select import (
    Selected,
    SelectError,
    SelectErrorGroup,
    UnhandledSelectedError,
    select,
    selected_from,
)
from ._timer import (
    MissedTickPolicy,
    SkipMissedAndDrift,
    SkipMissedAndResync,
    Timer,
    TriggerAllMissed,
)

__all__ = [
    "Event",
    "FileWatcher",
    "Merge",
    "MergeNamed",
    "MissedTickPolicy",
    "SelectError",
    "SelectErrorGroup",
    "Selected",
    "SkipMissedAndDrift",
    "SkipMissedAndResync",
    "Timer",
    "TriggerAllMissed",
    "UnhandledSelectedError",
    "select",
    "selected_from",
]
