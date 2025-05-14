# License: MIT
# Copyright © 2025 Frequenz Energy-as-a-Service GmbH

"""A receiver that will wait indefinitely if there is no underlying receiver.

The `OptionalReceiver` is useful when the underlying receiver is not set initially.
Instead of making `if-else` branches to check if the receiver is set, you can use
this receiver to wait indefinitely if it is not set.
"""

import asyncio

from typing_extensions import deprecated, override

from frequenz.channels import Receiver, ReceiverError, ReceiverMessageT_co


@deprecated("Use `frequenz.channels.experimental.NopReceiver` instead.")
class OptionalReceiver(Receiver[ReceiverMessageT_co]):
    """A receiver that will wait indefinitely if there is no underlying receiver.

    This receiver is useful when the underlying receiver is not set initially.
    Instead of making `if-else` branches to check if the receiver is set, you can use
    this receiver to wait indefinitely if it is not set.
    """

    def __init__(self, receiver: Receiver[ReceiverMessageT_co] | None):
        """Initialize this instance.

        Args:
            receiver: The underlying receiver, or `None` if there is no receiver.
        """
        self._receiver: Receiver[ReceiverMessageT_co] | None = receiver

    @override
    async def ready(self) -> bool:
        """Wait until the receiver is ready with a message or an error.

        Once a call to `ready()` has finished, the message should be read with
        a call to `consume()` (`receive()` or iterated over). The receiver will
        remain ready (this method will return immediately) until it is
        consumed.

        Returns:
            Whether the receiver is still active.
        """
        if self._receiver is not None:
            return await self._receiver.ready()

        # If there's no receiver, wait forever
        await asyncio.Event().wait()
        return False

    @override
    def consume(self) -> ReceiverMessageT_co:  # noqa: DOC503 (raised indirectly)
        """Return the latest from the underlying receiver message once `ready()` is complete.

        `ready()` must be called before each call to `consume()`.

        Returns:
            The next message received.

        Raises:
            ReceiverStoppedError: If the receiver stopped producing messages.
            ReceiverError: If there is some problem with the underlying receiver.
        """
        if self._receiver is None:
            raise ReceiverError(
                "`consume()` must be preceded by a call to `ready()`", self
            )
        return self._receiver.consume()

    def is_set(self) -> bool:
        """Check if the receiver is set."""
        return self._receiver is not None

    def close(self) -> None:
        """Stop the receiver."""
        if self._receiver is not None:
            self._receiver.close()
