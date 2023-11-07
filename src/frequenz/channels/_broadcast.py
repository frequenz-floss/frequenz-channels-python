# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A channel to broadcast messages to all receivers."""

from __future__ import annotations

import logging
import weakref
from asyncio import Condition
from collections import deque
from typing import Generic

from ._base_classes import Receiver as BaseReceiver
from ._base_classes import Sender as BaseSender
from ._base_classes import T
from ._exceptions import ChannelClosedError, ReceiverStoppedError, SenderError

_logger = logging.Logger(__name__)


class Broadcast(Generic[T]):
    """A channel to broadcast messages to multiple receivers.

    `Broadcast` channels can have multiple senders and multiple receivers. Each
    message sent through any of the senders is received by all of the
    receivers.

    Internally, a broadcast receiver's buffer is implemented with just
    append/pop operations on either side of a [deque][collections.deque], which
    are thread-safe.  Because of this, `Broadcast` channels are thread-safe.

    When there are multiple channel receivers, they can be awaited
    simultaneously using [select][frequenz.channels.util.select],
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

    def __init__(self, *, name: str, resend_latest: bool = False) -> None:
        """Create a Broadcast channel.

        Args:
            name: The name of the channel. This is for logging purposes, and it will be
                shown in the string representation of the channel.
            resend_latest: When True, every time a new receiver is created with
                `new_receiver`, it will automatically get sent the latest value on the
                channel.  This allows new receivers on slow streams to get the latest
                value as soon as they are created, without having to wait for the next
                message on the channel to arrive.  It is safe to be set in
                data/reporting channels, but is not recommended for use in channels that
                stream control instructions.
        """
        self._name: str = name
        """The name of the broadcast channel.

        Only used for debugging purposes.
        """

        self._recv_cv: Condition = Condition()
        """The condition to wait for data in the channel's buffer."""

        self._receivers: dict[int, weakref.ReferenceType[Receiver[T]]] = {}
        """The receivers attached to the channel, indexed by their hash()."""

        self._closed: bool = False
        """Whether the channel is closed."""

        self._latest: T | None = None
        """The latest value sent to the channel."""

        self.resend_latest: bool = resend_latest
        """Whether to resend the latest value to new receivers.

        When `True`, every time a new receiver is created with `new_receiver`, it will
        automatically get sent the latest value on the channel.  This allows new
        receivers on slow streams to get the latest value as soon as they are created,
        without having to wait for the next message on the channel to arrive.

        It is safe to be set in data/reporting channels, but is not recommended for use
        in channels that stream control instructions.
        """

    @property
    def name(self) -> str:
        """The name of this channel.

        This is for logging purposes, and it will be shown in the string representation
        of this channel.
        """
        return self._name

    @property
    def is_closed(self) -> bool:
        """Whether this channel is closed.

        Any further attempts to use this channel after it is closed will result in an
        exception.
        """
        return self._closed

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
        self._closed = True
        async with self._recv_cv:
            self._recv_cv.notify_all()

    def new_sender(self) -> Sender[T]:
        """Create a new broadcast sender.

        Returns:
            A Sender instance attached to the broadcast channel.
        """
        return Sender(self)

    def new_receiver(self, *, name: str | None = None, limit: int = 50) -> Receiver[T]:
        """Create a new broadcast receiver.

        Broadcast receivers have their own buffer, and when messages are not
        being consumed fast enough and the buffer fills up, old messages will
        get dropped just in this receiver.

        Args:
            name: A name to identify the receiver in the logs.
            limit: Number of messages the receiver can hold in its buffer.

        Returns:
            A Receiver instance attached to the broadcast channel.
        """
        recv: Receiver[T] = Receiver(name, limit, self)
        self._receivers[hash(recv)] = weakref.ref(recv)
        if self.resend_latest and self._latest is not None:
            recv.enqueue(self._latest)
        return recv

    def __str__(self) -> str:
        """Return a string representation of this receiver."""
        return f"{type(self).__name__}:{self._name}"

    def __repr__(self) -> str:
        """Return a string representation of this channel."""
        return (
            f"{type(self).__name__}(name={self._name!r}, "
            f"resend_latest={self.resend_latest!r}):<"
            f"latest={self._latest!r}, "
            f"receivers={len(self._receivers)!r}, "
            f"closed={self._closed!r}>"
        )


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
        self._chan: Broadcast[T] = chan
        """The broadcast channel this sender belongs to."""

    async def send(self, msg: T) -> None:
        """Send a message to all broadcast receivers.

        Args:
            msg: The message to be broadcast.

        Raises:
            SenderError: if the underlying channel was closed.
                A [ChannelClosedError][frequenz.channels.ChannelClosedError] is
                set as the cause.
        """
        # pylint: disable=protected-access
        if self._chan._closed:
            raise SenderError("The channel was closed", self) from ChannelClosedError(
                self._chan
            )
        self._chan._latest = msg
        stale_refs = []
        for _hash, recv_ref in self._chan._receivers.items():
            recv = recv_ref()
            if recv is None:
                stale_refs.append(_hash)
                continue
            recv.enqueue(msg)
        for _hash in stale_refs:
            del self._chan._receivers[_hash]
        async with self._chan._recv_cv:
            self._chan._recv_cv.notify_all()
        # pylint: enable=protected-access

    def __str__(self) -> str:
        """Return a string representation of this sender."""
        return f"{self._chan}:{type(self).__name__}"

    def __repr__(self) -> str:
        """Return a string representation of this sender."""
        return f"{type(self).__name__}({self._chan!r})"


class Receiver(BaseReceiver[T]):
    """A receiver to receive messages from the broadcast channel.

    Should not be created directly, but through the
    [Broadcast.new_receiver()][frequenz.channels.Broadcast.new_receiver]
    method.
    """

    def __init__(self, name: str | None, limit: int, chan: Broadcast[T]) -> None:
        """Create a broadcast receiver.

        Broadcast receivers have their own buffer, and when messages are not
        being consumed fast enough and the buffer fills up, old messages will
        get dropped just in this receiver.

        Args:
            name: A name to identify the receiver in the logs. If `None` an
                `id(self)`-based name will be used.  This is only for debugging
                purposes, it will be shown in the string representation of the
                receiver.
            limit: Number of messages the receiver can hold in its buffer.
            chan: a reference to the Broadcast channel that this receiver
                belongs to.
        """
        self._name: str = name if name is not None else f"{id(self):_}"
        """The name to identify the receiver.

        Only used for debugging purposes.
        """

        self._chan: Broadcast[T] = chan
        """The broadcast channel that this receiver belongs to."""

        self._q: deque[T] = deque(maxlen=limit)
        """The receiver's internal message queue."""

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
            _logger.warning(
                "Broadcast receiver [%s] is full. Oldest message was dropped.",
                self,
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

        # Use a while loop here, to handle spurious wakeups of condition variables.
        #
        # The condition also makes sure that if there are already messages ready to be
        # consumed, then we return immediately.
        # pylint: disable=protected-access
        while len(self._q) == 0:
            if self._chan._closed:
                return False
            async with self._chan._recv_cv:
                await self._chan._recv_cv.wait()
        return True
        # pylint: enable=protected-access

    def consume(self) -> T:
        """Return the latest value once `ready` is complete.

        Returns:
            The next value that was received.

        Raises:
            ReceiverStoppedError: if there is some problem with the receiver.
        """
        if not self._q and self._chan._closed:  # pylint: disable=protected-access
            raise ReceiverStoppedError(self) from ChannelClosedError(self._chan)

        assert self._q, "`consume()` must be preceded by a call to `ready()`"
        return self._q.popleft()

    def __str__(self) -> str:
        """Return a string representation of this receiver."""
        return f"{self._chan}:{type(self).__name__}"

    def __repr__(self) -> str:
        """Return a string representation of this receiver."""
        limit = self._q.maxlen
        assert limit is not None
        return (
            f"{type(self).__name__}(name={self._name!r}, limit={limit!r}, "
            f"{self._chan!r}):<id={id(self)!r}, used={len(self._q)!r}>"
        )
