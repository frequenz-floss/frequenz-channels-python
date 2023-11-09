# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Frequenz Channels.

This package contains
[channel](https://en.wikipedia.org/wiki/Channel_(programming)) implementations.

Base classes:

* [Receiver][frequenz.channels.Receiver]: An object that can wait for and
  consume messages from a channel.

* [Sender][frequenz.channels.Sender]: An object that can send messages to
  a channel.

Channels:

* [Anycast][frequenz.channels.Anycast]: A channel that supports multiple
  senders and multiple receivers.  A message sent through a sender will be
  received by exactly one receiver.

* [Broadcast][frequenz.channels.Broadcast]: A channel to broadcast messages
  from multiple senders to multiple receivers. Each message sent through any of
  the senders is received by all of the receivers.

Utilities to work with channels:

* [Merge][frequenz.channels.Merge]: A [Receiver][frequenz.channels.Receiver] that merges
  messages coming from multiple receivers into a single stream.

* [select][frequenz.channels.select]:  Iterate over the values of all
  [receivers][frequenz.channels.Receiver] as new values become available.

Exception classes:

* [Error][frequenz.channels.Error]: Base class for all errors in this
  library.

* [ChannelError][frequenz.channels.ChannelError]: Base class for all errors
  related to channels.

* [ChannelClosedError][frequenz.channels.ChannelClosedError]: Error raised when
  trying to operate (send, receive, etc.) through a closed channel.

* [SenderError][frequenz.channels.SenderError]: Base class for all errors
  related to senders.

* [ReceiverError][frequenz.channels.ReceiverError]: Base class for all errors
  related to receivers.

* [ReceiverStoppedError][frequenz.channels.ReceiverStoppedError]: A receiver
  stopped producing messages.

* [SelectError][frequenz.channels.SelectError]: Base class for all errors
    related to [select][frequenz.channels.select].

* [SelectErrorGroup][frequenz.channels.SelectErrorGroup]: A group of errors
    raised by [select][frequenz.channels.select].

* [UnhandledSelectedError][frequenz.channels.UnhandledSelectedError]: An error
    raised by [select][frequenz.channels.select] that was not handled by the
    user.

Extra utility receivers:

* [Event][frequenz.channels.event.Event]: A receiver that generates a message when
  an event is set.

* [FileWatcher][frequenz.channels.file_watcher.FileWatcher]: A receiver that
  generates a message when a file is added, modified or deleted.

* [Timer][frequenz.channels.timer.Timer]: A receiver that generates a message after a
  given amount of time.
"""

from ._anycast import Anycast
from ._broadcast import Broadcast
from ._exceptions import ChannelClosedError, ChannelError, Error
from ._merge import Merge
from ._receiver import Receiver, ReceiverError, ReceiverStoppedError
from ._select import (
    Selected,
    SelectError,
    SelectErrorGroup,
    UnhandledSelectedError,
    select,
    selected_from,
)
from ._sender import Sender, SenderError

__all__ = [
    "Anycast",
    "Broadcast",
    "ChannelClosedError",
    "ChannelError",
    "Error",
    "Merge",
    "Receiver",
    "ReceiverError",
    "ReceiverStoppedError",
    "SelectError",
    "SelectErrorGroup",
    "Selected",
    "Sender",
    "SenderError",
    "UnhandledSelectedError",
    "select",
    "selected_from",
]
