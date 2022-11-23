# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Frequenz Channels.

This package contains
[channel](https://en.wikipedia.org/wiki/Channel_(programming)) implementations.

Channels:

* [Anycast][frequenz.channels.Anycast]: A channel that supports multiple
  senders and multiple receivers.  A message sent through a sender will be
  received by exactly one receiver.

* [Bidirectional][frequenz.channels.Bidirectional]: A channel providing
  a `client` and a `service` handle to send and receive bidirectionally.

* [Broadcast][frequenz.channels.Broadcast]: A channel to broadcast messages
  from multiple senders to multiple receivers. Each message sent through any of
  the senders is received by all of the receivers.

Other base classes:

* [Peekable][frequenz.channels.Peekable]: An object to allow users to get
  a peek at the latest value in the channel, without consuming anything.

* [Receiver][frequenz.channels.Receiver]: An object that can wait for and
  consume messages from a channel.

* [Sender][frequenz.channels.Sender]: An object that can send messages to
  a channel.

Utilities:

* [util][frequenz.channels.util]: A module with utilities, like special
  receivers that implement timers, file watchers, merge receivers, or wait for
  messages in multiple channels.

Exception classes:

* [ChannelError][frequenz.channels.ChannelError]: Base class for all errors
  related to channels.

* [ChannelClosedError][frequenz.channels.ChannelClosedError]: Error raised when
  trying to operate (send, receive, etc.) through a closed channel.
"""

from . import util
from ._anycast import Anycast
from ._base_classes import ChannelClosedError, ChannelError, Peekable, Receiver, Sender
from ._bidirectional import Bidirectional
from ._broadcast import Broadcast

__all__ = [
    "Anycast",
    "Bidirectional",
    "Broadcast",
    "ChannelClosedError",
    "ChannelError",
    "Peekable",
    "Receiver",
    "Sender",
    "util",
]
