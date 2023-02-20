# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A channel to broadcast messages to all receivers."""

from __future__ import annotations

import logging
import weakref
from asyncio import Condition
from collections import deque
from typing import Deque, Dict, Generic, Optional
from uuid import UUID, uuid4

from ._base_classes import Peekable as BasePeekable
from ._base_classes import Receiver as BaseReceiver
from ._base_classes import Sender as BaseSender
from ._base_classes import T
from ._exceptions import (
    ChannelClosedError,
    ReceiverInvalidatedError,
    ReceiverStoppedError,
    SenderError,
)

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


        bcast = channel.Broadcast()

        sender = bcast.new_sender()
        receiver_1 = bcast.new_receiver()

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
                `new_receiver`, it will automatically get sent the latest value
                on the channel.  This allows new receivers on slow streams to
                get the latest value as soon as they are created, without having
                to wait for the next message on the channel to arrive.
        """
        self.name: str = name
        self._resend_latest = resend_latest

        self.recv_cv: Condition = Condition()
        self.receivers: Dict[UUID, weakref.ReferenceType[Receiver[T]]] = {}
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

    def new_sender(self) -> Sender[T]:
        """Create a new broadcast sender.

        Returns:
            A Sender instance attached to the broadcast channel.
        """
        return Sender(self)

    def new_receiver(
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
        self.receivers[uuid] = weakref.ref(recv)
        if self._resend_latest and self._latest is not None:
            recv.enqueue(self._latest)
        return recv

    def new_peekable(self) -> Peekable[T]:
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
    [Broadcast.new_sender()][frequenz.channels.Broadcast.new_sender]
    method.
    """

    def __init__(self, chan: Broadcast[T]) -> None:
        """Create a Broadcast sender.

        Args:
            chan: A reference to the broadcast channel this sender belongs to.
        """
        self._chan = chan

    async def send(self, msg: T) -> None:
        """Send a message to all broadcast receivers.

        Args:
            msg: The message to be broadcast.

        Raises:
            SenderError: if the underlying channel was closed.
                A [ChannelClosedError][frequenz.channels.ChannelClosedError] is
                set as the cause.
        """
        if self._chan.closed:
            raise SenderError("The channel was closed", self) from ChannelClosedError(
                self._chan
            )
        # pylint: disable=protected-access
        self._chan._latest = msg
        stale_refs = []
        for name, recv_ref in self._chan.receivers.items():
            recv = recv_ref()
            if recv is None:
                stale_refs.append(name)
                continue
            recv.enqueue(msg)
        for name in stale_refs:
            del self._chan.receivers[name]
        async with self._chan.recv_cv:
            self._chan.recv_cv.notify_all()


class Receiver(BaseReceiver[T]):
    """A receiver to receive messages from the broadcast channel.

    Should not be created directly, but through the
    [Broadcast.new_receiver()][frequenz.channels.Broadcast.new_receiver]
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

    async def ready(self) -> bool:
        """Wait until the receiver is ready with a value or an error.

        Once a call to `ready()` has finished, the value should be read with
        a call to `consume()` (`receive()` or iterated over). The receiver will
        remain ready (this method will return immediately) until it is
        consumed.

        Returns:
            Whether the receiver is still active.
        """
        # if there are still messages to consume from the queue, return immediately
        if self._q:
            return True

        # if it is not longer active, return immediately
        if not self._active:
            return False

        # Use a while loop here, to handle spurious wakeups of condition variables.
        #
        # The condition also makes sure that if there are already messages ready to be
        # consumed, then we return immediately.
        while len(self._q) == 0:
            if self._chan.closed:
                return False
            async with self._chan.recv_cv:
                await self._chan.recv_cv.wait()
        return True

    def _deactivate(self) -> None:
        """Set the receiver as inactive and remove it from the channel."""
        self._active = False
        if self._uuid in self._chan.receivers:
            del self._chan.receivers[self._uuid]

    def consume(self) -> T:
        """Return the latest value once `ready` is complete.

        Returns:
            The next value that was received.

        Raises:
            ReceiverStoppedError: if there is some problem with the receiver.
            ReceiverInvalidatedError: if the receiver was converted into
                a peekable.
        """
        if not self._q and not self._active:
            raise ReceiverInvalidatedError(
                "This receiver was converted into a Peekable so it is not longer valid.",
                self,
            )

        if not self._q and self._chan.closed:
            raise ReceiverStoppedError(self) from ChannelClosedError(self._chan)

        assert self._q, "`consume()` must be preceeded by a call to `ready()`"
        return self._q.popleft()

    def into_peekable(self) -> Peekable[T]:
        """Convert the `Receiver` implementation into a `Peekable`.

        Once this function has been called, the receiver will no longer be
        usable, and calling [receive()][frequenz.channels.Receiver.receive] on
        the receiver will raise an exception.

        Returns:
            A `Peekable` instance.
        """
        self._deactivate()
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
