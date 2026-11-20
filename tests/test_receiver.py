# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the Receiver base class."""

from frequenz.channels import Receiver


def test_close_is_abstract() -> None:
    """Test that a receiver subclass has to implement `close()`."""
    assert "close" in Receiver.__abstractmethods__
