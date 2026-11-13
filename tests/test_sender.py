# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the sender errors."""

from frequenz.channels import (
    BroadcastChannel,
    SenderClosedError,
    SenderError,
    SenderHasNoReceiversError,
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


def test_sender_has_no_receivers_error() -> None:
    """Ensure having no receivers is a transient sender error."""
    sender, _receiver = BroadcastChannel[int](name="test")
    error = SenderHasNoReceiversError(sender)

    assert isinstance(error, TransientSenderError)
    assert isinstance(error, SenderError)
    assert error.sender is sender
    assert str(error) == f"Sender {sender} has no receivers"
