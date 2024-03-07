# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Sender interface and related exceptions.

# Senders

Messages are sent to a [channel](/user-guide/channels) through
[Sender][frequenz.channels.Sender] objects. [Senders][frequenz.channels.Sender] are
usually created by calling `channel.new_sender()`, and are a very simple abstraction
that only provides a single [`send()`][frequenz.channels.Sender.send] method:

```python show_lines="6:"
from frequenz.channels import Anycast

channel = Anycast[int](name="test-channel")
sender = channel.new_sender()

await sender.send("Hello, world!")
```

Although [`send()`][frequenz.channels.Sender.send] is an asynchronous method, some
channels may implement it in a synchronous, non-blocking way. For example, buffered
channels that drop messages when the buffer is full could guarantee that
[`send()`][frequenz.channels.Sender.send] never blocks. However, please keep in mind
that the [asyncio][] event loop could give control to another task at any time,
effectively making the [`send()`][frequenz.channels.Sender.send] method blocking.

# Error Handling

!!! Tip inline end

    For more information about handling errors, please refer to the
    [Error Handling](/user-guide/error-handling/) section of the user guide.

If there is any failure sending a message,
a [SenderError][frequenz.channels.SenderError] exception is raised.

```python show_lines="6:"
from frequenz.channels import Anycast

channel = Anycast[int](name="test-channel")
sender = channel.new_sender()

try:
    await sender.send("Hello, world!")
except SenderError as error:
    print(f"Error sending message: {error}")
```
"""

from abc import ABC, abstractmethod
from typing import Generic

from ._exceptions import Error
from ._generic import SenderMessageT_co, SenderMessageT_contra


class Sender(ABC, Generic[SenderMessageT_contra]):
    """An endpoint to sends messages."""

    @abstractmethod
    async def send(self, message: SenderMessageT_contra, /) -> None:
        """Send a message.

        Args:
            message: The message to be sent.

        Raises:
            SenderError: If there was an error sending the message.
        """


class SenderError(Error, Generic[SenderMessageT_co]):
    """An error that originated in a [Sender][frequenz.channels.Sender].

    All exceptions generated by senders inherit from this exception.
    """

    def __init__(self, message: str, sender: Sender[SenderMessageT_co]):
        """Initialize this error.

        Args:
            message: The error message.
            sender: The [Sender][frequenz.channels.Sender] where the error
                happened.
        """
        super().__init__(message)
        self.sender: Sender[SenderMessageT_co] = sender
        """The sender where the error happened."""
