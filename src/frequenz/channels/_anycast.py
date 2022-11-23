# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A channel for sending data across async tasks."""

from __future__ import annotations

from asyncio import Condition
from collections import deque
from typing import Deque, Generic, Optional

from ._base_classes import ChannelClosedError
from ._base_classes import Receiver as BaseReceiver
from ._base_classes import Sender as BaseSender
from ._base_classes import T


class Anycast(Generic[T]):
    """A channel for sending data across async tasks.

    Anycast channels support multiple senders and multiple receivers.  A message sent
    through a sender will be received by exactly one receiver.

    In cases where each message need to be received by every receiver, a
    [Broadcast][frequenz.channels.Broadcast] channel may be used.

    Uses an [deque][collections.deque] internally, so Anycast channels are not
    thread-safe.

    When there are multiple channel receivers, they can be awaited
    simultaneously using [Select][frequenz.channels.util.Select],
    [Merge][frequenz.channels.util.Merge] or
    [MergeNamed][frequenz.channels.util.MergeNamed].

    Example:
        ``` python
        async def send(sender: channel.Sender) -> None:
            while True:
                next = random.randint(3, 17)
                print(f"sending: {next}")
                await sender.send(next)


        async def recv(id: int, receiver: channel.Receiver) -> None:
            while True:
                next = await receiver.receive()
                print(f"receiver_{id} received {next}")
                await asyncio.sleep(0.1) # sleep (or work) with the data


        acast = channel.Anycast()

        sender = acast.new_sender()
        receiver_1 = acast.new_receiver()

        asyncio.create_task(send(sender))

        await recv(1, receiver_1)
        ```

        Check the `tests` and `benchmarks` directories for more examples.
    """

    def __init__(self, maxsize: int = 10) -> None:
        """Create an Anycast channel.

        Args:
            maxsize: Size of the channel's buffer.
        """
        self.limit: int = maxsize
        self.deque: Deque[T] = deque(maxlen=maxsize)
        self.send_cv: Condition = Condition()
        self.recv_cv: Condition = Condition()
        self.closed: bool = False

    async def close(self) -> None:
        """Close the channel.

        Any further attempts to [send()][frequenz.channels.Sender.send] data
        will return `False`.

        Receivers will still be able to drain the pending items on the channel,
        but after that, subsequent
        [receive()][frequenz.channels.Receiver.receive] calls will return `None`
        immediately.

        """
        self.closed = True
        async with self.send_cv:
            self.send_cv.notify_all()
        async with self.recv_cv:
            self.recv_cv.notify_all()

    def new_sender(self) -> Sender[T]:
        """Create a new sender.

        Returns:
            A Sender instance attached to the Anycast channel.
        """
        return Sender(self)

    def new_receiver(self) -> Receiver[T]:
        """Create a new receiver.

        Returns:
            A Receiver instance attached to the Anycast channel.
        """
        return Receiver(self)


class Sender(BaseSender[T]):
    """A sender to send messages to an Anycast channel.

    Should not be created directly, but through the `Anycast.ggetet_sender()`
    method.
    """

    def __init__(self, chan: Anycast[T]) -> None:
        """Create a channel sender.

        Args:
            chan: A reference to the channel that this sender belongs to.
        """
        self._chan = chan

    async def send(self, msg: T) -> bool:
        """Send a message across the channel.

        To send, this method inserts the message into the Anycast channel's
        buffer.  If the channel's buffer is full, waits for messages to get
        consumed, until there's some free space available in the buffer.  Each
        message will be received by exactly one receiver.

        Args:
            msg: The message to be sent.

        Returns:
            Whether the message was sent, based on whether the channel is open
                or not.
        """
        if self._chan.closed:
            return False
        while len(self._chan.deque) == self._chan.deque.maxlen:
            async with self._chan.send_cv:
                await self._chan.send_cv.wait()
        self._chan.deque.append(msg)
        async with self._chan.recv_cv:
            self._chan.recv_cv.notify(1)
        return True


class Receiver(BaseReceiver[T]):
    """A receiver to receive messages from an Anycast channel.

    Should not be created directly, but through the `Anycast.new_receiver()`
    method.
    """

    def __init__(self, chan: Anycast[T]) -> None:
        """Create a channel receiver.

        Args:
            chan: A reference to the channel that this receiver belongs to.
        """
        self._chan = chan
        self._next: Optional[T] = None

    async def ready(self) -> None:
        """Wait until the receiver is ready with a value.

        Raises:
            ChannelClosedError: if the underlying channel is closed.
        """
        # if a message is already ready, then return immediately.
        if self._next is not None:
            return

        while len(self._chan.deque) == 0:
            if self._chan.closed:
                raise ChannelClosedError()
            async with self._chan.recv_cv:
                await self._chan.recv_cv.wait()
        self._next = self._chan.deque.popleft()
        async with self._chan.send_cv:
            self._chan.send_cv.notify(1)

    def consume(self) -> T:
        """Return the latest value once `ready()` is complete.

        Returns:
            The next value that was received.
        """
        assert (
            self._next is not None
        ), "calls to `consume()` must be follow a call to `ready()`"
        next_val = self._next
        self._next = None
        return next_val
