# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A channel to broadcast messages to all receivers."""

from __future__ import annotations

import logging
from asyncio import Condition
from collections import deque
from typing import Deque, Dict, Generic, Optional
from uuid import UUID, uuid4

from frequenz.channels.base_classes import BufferedReceiver
from frequenz.channels.base_classes import Peekable as BasePeekable
from frequenz.channels.base_classes import Sender as BaseSender
from frequenz.channels.base_classes import T

logger = logging.Logger(__name__)


class Broadcast(Generic[T]):
    """A channel to broadcast messages to multiple receivers.

    `Broadcast` channels can have multiple senders and multiple receivers. Each
    message sent through any of the senders is received by all of the
    receivers.

    Internally, a broadcast receiver's buffer is implemented with just
    append/pop operations on either side of a [deque][collections.deque], which
    are thread-safe.  Because of this, `Broadcast` channels are thread-safe.

    When there are multiple channel receivers, they can be awaited
    simultaneously using [Select][frequenz.channels.Select],
    [Merge][frequenz.channels.Merge] or
    [MergeNamed][frequenz.channels.MergeNamed].

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


        bcast = channel.Broadcast()

        sender = bcast.get_sender()
        receiver_1 = bcast.get_receiver()

        asyncio.create_task(send(sender))

        await recv(1, receiver_1)
        ```

        Check the `tests` and `benchmarks` directories for more examples.
    """

    def __init__(self, name: str, resend_latest: bool = False) -> None:
        """Create a Broadcast channel.

        Args:
            name: A name for the broadcast channel, typically based on the type
                of data sent through it.  Used to identify the channel in the
                logs.
            resend_latest: When True, every time a new receiver is created with
                `get_receiver`, it will automatically get sent the latest value
                on the channel.  This allows new receivers on slow streams to
                get the latest value as soon as they are created, without having
                to wait for the next message on the channel to arrive.
        """
        self.name: str = name
        self._resend_latest = resend_latest

        self.recv_cv: Condition = Condition()
        self.receivers: Dict[UUID, Receiver[T]] = {}
        self.closed: bool = False
        self._latest: Optional[T] = None

    async def close(self) -> None:
        """Close the Broadcast channel.

        Any further attempts to [send()][frequenz.channels.Sender.send] data
        will return `False`.

        Receivers will still be able to drain the pending items on their queues,
        but after that, subsequent
        [receive()][frequenz.channels.Receiver.receive] calls will return `None`
        immediately.
        """
        self._latest = None
        self.closed = True
        async with self.recv_cv:
            self.recv_cv.notify_all()

    def _drop_receiver(self, uuid: UUID) -> None:
        """Drop a specific receiver from the list of broadcast receivers.

        Called from the destructors of receivers.

        Args:
            uuid: a uuid identifying the receiver to be dropped.
        """
        if uuid in self.receivers:
            del self.receivers[uuid]

    def get_sender(self) -> Sender[T]:
        """Create a new broadcast sender.

        Returns:
            A Sender instance attached to the broadcast channel.
        """
        return Sender(self)

    def get_receiver(
        self, name: Optional[str] = None, maxsize: int = 50
    ) -> Receiver[T]:
        """Create a new broadcast receiver.

        Broadcast receivers have their own buffer, and when messages are not
        being consumed fast enough and the buffer fills up, old messages will
        get dropped just in this receiver.

        Args:
            name: A name to identify the receiver in the logs.
            maxsize: Size of the receiver's buffer.

        Returns:
            A Receiver instance attached to the broadcast channel.
        """
        uuid = uuid4()
        if name is None:
            name = str(uuid)
        recv: Receiver[T] = Receiver(uuid, name, maxsize, self)
        self.receivers[uuid] = recv
        if self._resend_latest and self._latest is not None:
            recv.enqueue(self._latest)
        return recv

    def get_peekable(self) -> Peekable[T]:
        """Create a new Peekable for the broadcast channel.

        A Peekable provides a [peek()][frequenz.channels.Peekable.peek] method
        that allows the user to get a peek at the latest value in the channel,
        without consuming anything.

        Returns:
            A Peekable to peek into the broadcast channel with.
        """
        return Peekable(self)


class Sender(BaseSender[T]):
    """A sender to send messages to the broadcast channel.

    Should not be created directly, but through the
    [Broadcast.get_sender()][frequenz.channels.Broadcast.get_sender]
    method.
    """

    def __init__(self, chan: Broadcast[T]) -> None:
        """Create a Broadcast sender.

        Args:
            chan: A reference to the broadcast channel this sender belongs to.
        """
        self._chan = chan

    async def send(self, msg: T) -> bool:
        """Send a message to all broadcast receivers.

        Args:
            msg: The message to be broadcast.

        Returns:
            Whether the message was sent, based on whether the broadcast
                channel is open or not.
        """
        if self._chan.closed:
            return False
        # pylint: disable=protected-access
        self._chan._latest = msg
        for recv in self._chan.receivers.values():
            recv.enqueue(msg)
        async with self._chan.recv_cv:
            self._chan.recv_cv.notify_all()
        return True


class Receiver(BufferedReceiver[T]):
    """A receiver to receive messages from the broadcast channel.

    Should not be created directly, but through the
    [Broadcast.get_receiver()][frequenz.channels.Broadcast.get_receiver]
    method.
    """

    def __init__(self, uuid: UUID, name: str, maxsize: int, chan: Broadcast[T]) -> None:
        """Create a broadcast receiver.

        Broadcast receivers have their own buffer, and when messages are not
        being consumed fast enough and the buffer fills up, old messages will
        get dropped just in this receiver.

        Args:
            uuid: A uuid to identify the receiver in the broadcast channel's
                list of receivers.
            name: A name to identify the receiver in the logs.
            maxsize: Size of the receiver's buffer.
            chan: a reference to the Broadcast channel that this receiver
                belongs to.
        """
        self._uuid = uuid
        self._name = name
        self._chan = chan
        self._q: Deque[T] = deque(maxlen=maxsize)

        self._active = True

    def __del__(self) -> None:
        """Drop this receiver from the list of Broadcast receivers."""
        if self._active:
            self._chan._drop_receiver(self._uuid)

    def enqueue(self, msg: T) -> None:
        """Put a message into this receiver's queue.

        To be called by broadcast senders.  If the receiver's queue is already
        full, drop the oldest message to make room for the incoming message, and
        log a warning.

        Args:
            msg: The message to be sent.
        """
        if len(self._q) == self._q.maxlen:
            self._q.popleft()
            logger.warning(
                "Broadcast receiver [%s:%s] is full. Oldest message was dropped.",
                self._chan.name,
                self._name,
            )
        self._q.append(msg)

    def __len__(self) -> int:
        """Return the number of unconsumed messages in the broadcast receiver.

        Returns:
            Number of items in the receiver's internal queue.
        """
        return len(self._q)

    async def receive(self) -> Optional[T]:
        """Receive a message from the Broadcast channel.

        Waits until there are messages available in the channel and returns
        them.  If there are no remaining messages in the buffer and the channel
        is closed, returns `None` immediately.

        If [into_peekable()][frequenz.channels.Receiver.into_peekable] is called
        on a broadcast `Receiver`, further calls to `receive`, will raise an
        `EOFError`.

        Raises:
            EOFError: when the receiver has been converted into a `Peekable`.

        Returns:
            `None`, if the channel is closed, a message otherwise.
        """
        if not self._active:
            raise EOFError("This receiver is no longer active.")

        while len(self._q) == 0:
            if self._chan.closed:
                return None
            async with self._chan.recv_cv:
                await self._chan.recv_cv.wait()
        ret = self._q.popleft()
        return ret

    def into_peekable(self) -> Peekable[T]:
        """Convert the `Receiver` implementation into a `Peekable`.

        Once this function has been called, the receiver will no longer be
        usable, and calling [receive()][frequenz.channels.Receiver.receive] on
        the receiver will raise an exception.

        Returns:
            A `Peekable` instance.
        """
        self._chan._drop_receiver(self._uuid)  # pylint: disable=protected-access
        self._active = False
        return Peekable(self._chan)


class Peekable(BasePeekable[T]):
    """A Peekable to peek into broadcast channels.

    A Peekable provides a [peek()][frequenz.channels.Peekable] method that
    allows the user to get a peek at the latest value in the channel, without
    consuming anything.
    """

    def __init__(self, chan: Broadcast[T]) -> None:
        """Create a `Peekable` instance.

        Args:
            chan: The broadcast channel this Peekable will try to peek into.
        """
        self._chan = chan

    def peek(self) -> Optional[T]:
        """Return the latest value that was sent to the channel.

        Returns:
            The latest value received by the channel, and `None`, if nothing
                has been sent to the channel yet, or if the channel is closed.
        """
        return self._chan._latest  # pylint: disable=protected-access
