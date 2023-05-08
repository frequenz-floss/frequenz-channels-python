# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Channel utilities.

A module with several utilities to work with channels:

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

* [Select][frequenz.channels.util.Select]: A helper to select the next
  available message for each [receiver][frequenz.channels.Receiver] in a group
  of receivers.
"""

from ._file_watcher import FileWatcher
from ._merge import Merge
from ._merge_named import MergeNamed
from ._select import Select
from ._timer import (
    MissedTickPolicy,
    SkipMissedAndDrift,
    SkipMissedAndResync,
    Timer,
    TriggerAllMissed,
)

__all__ = [
    "FileWatcher",
    "Merge",
    "MergeNamed",
    "MissedTickPolicy",
    "Timer",
    "Select",
    "SkipMissedAndDrift",
    "SkipMissedAndResync",
    "TriggerAllMissed",
]
