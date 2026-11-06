# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""A marker for arguments that take their value from the channel."""

from typing_extensions import sentinel

CHANNEL_DEFAULT = sentinel("CHANNEL_DEFAULT")
"""A marker for arguments that take their value from the channel.

Some methods take arguments that, when not given, use the value the channel was
created with, like the `block_on_full` argument of
[`BroadcastSender.subscribe()`][frequenz.channels.BroadcastSender.subscribe] and
[`BroadcastSender.send()`][frequenz.channels.BroadcastSender.send].
`CHANNEL_DEFAULT` is their default value, so passing it explicitly is the same as
not passing the argument at all.
"""
