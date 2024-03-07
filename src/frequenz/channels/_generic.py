# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Generic type variables."""

from typing import TypeVar

ChannelMessageT = TypeVar("ChannelMessageT")
"""The type of the message that can be sent across a channel."""

ErroredChannelT_co = TypeVar("ErroredChannelT_co", covariant=True)
"""The type of channel having an error."""

MappedMessageT_co = TypeVar("MappedMessageT_co", covariant=True)
"""The type of the message received by the receiver after being mapped."""

ReceiverMessageT_co = TypeVar("ReceiverMessageT_co", covariant=True)
"""The type of the message received by a receiver."""

SenderMessageT_co = TypeVar("SenderMessageT_co", covariant=True)
"""The type of the message sent by a sender."""

SenderMessageT_contra = TypeVar("SenderMessageT_contra", contravariant=True)
"""The type of the message sent by a sender."""
