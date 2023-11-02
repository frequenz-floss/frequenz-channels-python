# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Frequenz Channels.

This package contains
[channel](https://en.wikipedia.org/wiki/Channel_(programming)) implementations.

Main base classes and functions:

* [Sender][frequenz.channels.Sender]: An object that can send messages to
  a channel.

* [Receiver][frequenz.channels.Receiver]: An object that can wait for and
  consume messages from a channel.

* [selected()][frequenz.channels.select]: A function to wait on multiple
  receivers at once.

Channels:

* [Anycast][frequenz.channels.anycast.Anycast]: A channel that supports multiple
  senders and multiple receivers.  A message sent through a sender will be
  received by exactly one receiver.

* [Bidirectional][frequenz.channels.bidirectional.Bidirectional]: A channel providing
  a `client` and a `service` handle to send and receive bidirectionally.

* [Broadcast][frequenz.channels.broadcast.Broadcast]: A channel to broadcast messages
  from multiple senders to multiple receivers. Each message sent through any of
  the senders is received by all of the receivers.
"""

from ._exceptions import ChannelClosedError, ChannelError, Error
from ._receiver import (
    Peekable,
    Receiver,
    ReceiverError,
    ReceiverInvalidatedError,
    ReceiverStoppedError,
)
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
    "ChannelClosedError",
    "ChannelError",
    "Error",
    "Peekable",
    "Receiver",
    "ReceiverError",
    "ReceiverInvalidatedError",
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
