# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Frequenz Channels.

This package contains
[channel](https://en.wikipedia.org/wiki/Channel_(programming)) implementations.

<!-- For the full documentation and user guide please visit the [project's
website](https://frequenz-floss.github.io/frequenz-channels-python/) -->

Base classes:

* [`Receiver`][.Receiver]: An object that can wait for and
  consume messages from a channel.

* [`Sender`][.Sender]: An object that can send messages to
  a channel.

Channels:

* [`Anycast`][.Anycast]: A channel that supports multiple
  senders and multiple receivers.  A message sent through a sender will be
  received by exactly one receiver.

* [`Broadcast`][.Broadcast]: A channel to broadcast messages
  from multiple senders to multiple receivers. Each message sent through any of
  the senders is received by all of the receivers.

Utilities to work with channels:

* [`merge`][.merge]: Merge messages coming from multiple receivers into
  a single stream.

* [`select`][.select]: Iterate over the messages of all
  [receivers][.Receiver] as new messages become available.

* [`LatestValueCache`][.LatestValueCache]: A cache that stores
  the latest value in a receiver, providing a way to look up the latest value in
  a stream, without having to wait, as long as there has been one value
  received.

Exception classes:

* [`Error`][.Error]: Base class for all errors in this
  library.

* [`ChannelError`][.ChannelError]: Base class for all errors
  related to channels.

* [`ChannelClosedError`][.ChannelClosedError]: Error raised when
  trying to operate (send, receive, etc.) through a closed channel.

* [`SenderError`][.SenderError]: Base class for all errors
  related to senders.

* [`ReceiverError`][.ReceiverError]: Base class for all errors
  related to receivers.

* [`ReceiverStoppedError`][.ReceiverStoppedError]: A receiver
  stopped producing messages.

* [`SelectError`][.SelectError]: Base class for all errors
    related to [`select`][.select].

* [`UnhandledSelectedError`][.UnhandledSelectedError]: An error
    raised by [`select`][.select] that was not handled by the
    user.

Extra utility receivers:

* [`Event`][.event.Event]: A receiver that generates a message when
  an event is set.

* [`FileWatcher`][.file_watcher.FileWatcher]: A receiver that
  generates a message when a file is added, modified or deleted.

* [`Timer`][.timer.Timer]: A receiver that generates a message after a
  given amount of time.
"""

from ._anycast import Anycast
from ._broadcast import Broadcast, BroadcastChannel, BroadcastReceiver, BroadcastSender
from ._exceptions import ChannelClosedError, ChannelError, Error
from ._generic import (
    ChannelMessageT,
    ErroredChannelT_co,
    MappedMessageT_co,
    ReceiverMessageT_co,
    SenderMessageT_co,
    SenderMessageT_contra,
)
from ._latest_value_cache import LatestValueCache
from ._merge import Merger, merge
from ._oneshot import OneshotChannel, OneshotReceiver, OneshotSender
from ._receiver import Receiver, ReceiverError, ReceiverStoppedError
from ._select import (
    Selected,
    SelectError,
    UnhandledSelectedError,
    select,
    selected_from,
)
from ._sender import (
    CloneableSender,
    CloneableSubscribableSender,
    Sender,
    SenderClosedError,
    SenderError,
    SubscribableSender,
)

__all__ = [
    "Anycast",
    "Broadcast",
    "BroadcastChannel",
    "BroadcastReceiver",
    "BroadcastSender",
    "ChannelClosedError",
    "ChannelError",
    "ChannelMessageT",
    "CloneableSender",
    "CloneableSubscribableSender",
    "Error",
    "ErroredChannelT_co",
    "LatestValueCache",
    "MappedMessageT_co",
    "Merger",
    "OneshotChannel",
    "OneshotReceiver",
    "OneshotSender",
    "Receiver",
    "ReceiverError",
    "ReceiverMessageT_co",
    "ReceiverStoppedError",
    "SelectError",
    "Selected",
    "Sender",
    "SenderClosedError",
    "SenderError",
    "SenderMessageT_co",
    "SenderMessageT_contra",
    "SubscribableSender",
    "UnhandledSelectedError",
    "merge",
    "select",
    "selected_from",
]
