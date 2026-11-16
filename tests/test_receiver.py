# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the Receiver base class."""

import pytest

from frequenz.channels import Receiver


def test_receiver_without_close_cannot_be_instantiated() -> None:
    """Test that a receiver subclass has to implement `close()`."""

    class NoCloseReceiver(Receiver[int]):
        """A receiver that doesn't implement `close()`."""

        async def ready(self) -> bool:
            """Return that the receiver is not ready."""
            return False

        def consume(self) -> int:
            """Return a message."""
            return 0

    with pytest.raises(TypeError, match=r"abstract method.*close"):
        NoCloseReceiver()  # type: ignore[abstract]  # pylint: disable=abstract-class-instantiated
