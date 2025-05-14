# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""A receiver that will never receive a message.

It is useful as a place-holder receiver for use in contexts where a receiver is
necessary, but one is not available.
"""

import asyncio

from typing_extensions import override

from frequenz.channels import Receiver, ReceiverError, ReceiverMessageT_co
from frequenz.channels._receiver import ReceiverStoppedError


class NopReceiver(Receiver[ReceiverMessageT_co]):
    """A place-holder receiver that will never receive a message."""

    def __init__(self) -> None:
        """Initialize this instance."""
        self._closed: bool = False

    @override
    async def ready(self) -> bool:
        """Wait for ever unless the receiver is closed.

        Returns:
            Whether the receiver is still active.
        """
        if self._closed:
            return False
        await asyncio.Future()
        return False

    @override
    def consume(self) -> ReceiverMessageT_co:  # noqa: DOC503 (raised indirectly)
        """Raise `ReceiverError` unless the NopReceiver is closed.

        If the receiver is closed, then raise `ReceiverStoppedError`.

        Returns:
            The next message received.

        Raises:
            ReceiverStoppedError: If the receiver stopped producing messages.
            ReceiverError: If there is some problem with the underlying receiver.
        """
        if self._closed:
            raise ReceiverStoppedError(self)
        raise ReceiverError("`consume()` must be preceded by a call to `ready()`", self)

    @override
    def close(self) -> None:
        """Stop the receiver."""
        self._closed = True
