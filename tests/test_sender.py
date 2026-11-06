# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the sender errors."""

from frequenz.channels import (
    BroadcastChannel,
    SenderClosedError,
    SenderError,
    TransientSenderError,
)


def test_transient_sender_error() -> None:
    """Ensure transient errors are sender errors, and closed senders aren't transient."""
    sender, _receiver = BroadcastChannel[int](name="test")
    error = TransientSenderError("Not sent", sender)

    assert isinstance(error, SenderError)
    assert error.sender is sender
    assert str(error) == "Not sent"
    assert not issubclass(SenderClosedError, TransientSenderError)
