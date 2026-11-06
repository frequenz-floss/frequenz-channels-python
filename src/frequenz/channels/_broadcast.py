# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""A channel to broadcast messages to all receivers."""

# pylint: disable=too-many-lines

from __future__ import annotations

import logging
import weakref
from asyncio import Condition, Event
from collections import deque
from typing import Generic, TypeVar

from frequenz.core.warnings import ignoring_deprecations
from typing_extensions import deprecated, override

from ._channel_default import CHANNEL_DEFAULT
from ._exceptions import ChannelClosedError
from ._generic import ChannelMessageT
from ._receiver import Receiver, ReceiverStoppedError
from ._sender import CloneableSubscribableSender, SenderClosedError, SenderError

_logger = logging.getLogger(__name__)


@deprecated("Please use BroadcastChannel instead.")
class Broadcast(  # pylint: disable=too-many-instance-attributes
    Generic[ChannelMessageT]
):
    """A channel that delivers all messages to all receivers.

    # Description

    [`Broadcast`][frequenz.channels.Broadcast] channels can have multiple
    [senders][frequenz.channels.Sender] and multiple
    [receivers][frequenz.channels.Receiver]. Each message sent through any of the
    senders will be received by all receivers.

    <center>
    ```bob
    .---------. msg1                           msg1,msg2  .-----------.
    | Sender  +------.                        .---------->| Receiver  |
    '---------'      |      .----------.     |            '-----------'
                     +----->| Channel  +-----+
    .---------.      |      '----------'     |            .-----------.
    | Sender  +------'                       '----------->| Receiver  |
    '---------' msg2                           msg1,msg2  '-----------'
    ```
    </center>

    !!! Note inline end "Characteristics"

        * **Buffered:** Yes, with one buffer per receiver
        * **Buffer full policy:** Drop oldest message
        * **Multiple receivers:** Yes
        * **Multiple senders:** Yes
        * **Thread-safe:** No

    This channel is buffered, and when messages are not being consumed fast
    enough and the buffer fills up, old messages will get dropped.

    Each receiver has its own buffer, so messages will only be dropped for
    receivers that can't keep up with the senders, and not for the whole
    channel.

    To create a new [senders][frequenz.channels.Sender] and
    [receivers][frequenz.channels.Receiver] you can use the
    [`.new_sender()`][frequenz.channels.Broadcast.new_sender] and
    [`.new_receiver()`][frequenz.channels.Broadcast.new_receiver] methods
    respectively.

    When a channel is not needed anymore, it should be closed with
    [`.aclose()`][frequenz.channels.Broadcast.aclose]. This will prevent further
    attempts to [`send()`][frequenz.channels.Sender.send] data, and will allow
    receivers to drain the pending items on their queues, but after that,
    subsequent [`receive()`][frequenz.channels.Receiver.receive] calls will
    raise a [`ReceiverStoppedError`][frequenz.channels.ReceiverStoppedError].

    This channel is useful, for example, to implement a pub/sub pattern, where
    multiple receivers can subscribe to a channel to receive all messages.

    In cases where each message needs to be delivered only to one receiver, an
    [anycast][frequenz.channels.Anycast] channel may be used.

    # Examples

    Example: Send a few numbers to a receiver
        This is a very simple example that sends a few numbers from a single sender to
        a single receiver.

        ```python
        import asyncio

        from frequenz.channels import Broadcast, Sender


        async def send(sender: Sender[int]) -> None:
            for message in range(3):
                print(f"sending {message}")
                await sender.send(message)


        async def main() -> None:
            channel = Broadcast[int](name="numbers")

            sender = channel.new_sender()
            receiver = channel.new_receiver()

            async with asyncio.TaskGroup() as task_group:
                task_group.create_task(send(sender))
                for _ in range(3):
                    message = await receiver.receive()
                    print(f"received {message}")
                    await asyncio.sleep(0.1)  # sleep (or work) with the data


        asyncio.run(main())
        ```

        The output should look something like (although the sending and received might
        appear more interleaved):

        ```
        sending 0
        sending 1
        sending 2
        received 0
        received 1
        received 2
        ```

    Example: Send a few number from multiple senders to multiple receivers
        This is a more complex example that sends a few numbers from multiple senders to
        multiple receivers, using a small buffer to force the senders to block.

        ```python
        import asyncio

        from frequenz.channels import Broadcast, Receiver, ReceiverStoppedError, Sender


        async def send(name: str, sender: Sender[int], start: int, stop: int) -> None:
            for message in range(start, stop):
                print(f"{name} sending {message}")
                await sender.send(message)


        async def recv(name: str, receiver: Receiver[int]) -> None:
            try:
                async for message in receiver:
                    print(f"{name} received {message}")
                await asyncio.sleep(0.1)  # sleep (or work) with the data
            except ReceiverStoppedError:
                pass


        async def main() -> None:
            acast = Broadcast[int](name="numbers")

            async with asyncio.TaskGroup() as task_group:
                task_group.create_task(send("sender_1", acast.new_sender(), 10, 13))
                task_group.create_task(send("sender_2", acast.new_sender(), 20, 22))
                task_group.create_task(recv("receiver_1", acast.new_receiver()))
                task_group.create_task(recv("receiver_2", acast.new_receiver()))


        asyncio.run(main())
        ```

        The output should look something like this(although the sending and received
        might appear interleaved in a different way):

        ```
        sender_1 sending 10
        sender_1 sending 11
        sender_1 sending 12
        sender_2 sending 20
        sender_2 sending 21
        receiver_1 received 10
        receiver_1 received 11
        receiver_1 received 12
        receiver_1 received 20
        receiver_1 received 21
        receiver_2 received 10
        receiver_2 received 11
        receiver_2 received 12
        receiver_2 received 20
        receiver_2 received 21
        ```
    """

    def __init__(
        self,
        *,
        name: str,
        resend_latest: bool = False,
        auto_close: bool = False,
    ) -> None:
        """Initialize this channel.

        Args:
            name: The name of the channel. This is for logging purposes, and it will be
                shown in the string representation of the channel.
            resend_latest: When True, every time a new receiver is created with
                [`.new_receiver()`][frequenz.channels.Broadcast.new_receiver], the last
                message seen by the channel will be sent to the new receiver
                automatically. This allows new receivers on slow streams to get the
                latest message as soon as they are created, without having to wait for
                the next message on the channel to arrive.  It is safe to be set in
                data/reporting channels, but is not recommended for use in channels that
                stream control instructions.
            auto_close: If True, the channel will be closed when all senders or all
                receivers are closed.
        """
        self._name: str = name
        """The name of the broadcast channel.

        Only used for debugging purposes.
        """

        self._recv_cv: Condition = Condition()
        """The condition to wait for data in the channel's buffer."""

        self._sender_count: int = 0
        """The number of senders attached to this channel."""

        self._receivers: dict[
            int, weakref.ReferenceType[BroadcastReceiver[ChannelMessageT]]
        ] = {}
        """The receivers attached to the channel, indexed by their hash()."""

        self._blocking_receivers: dict[
            int, weakref.ReferenceType[BroadcastReceiver[ChannelMessageT]]
        ] = {}
        """The receivers created with `block_on_full=True`, indexed by their hash().

        They are in `_receivers` too.  Senders only check these for room before
        sending, so a channel without blocking receivers doesn't pay for it.
        """

        self._wake_senders_event: Event | None = None
        """The event senders wait on until blocking receivers have room.

        It is `None` while no sender waits.  Each wake-up sets it back to `None` and
        then sets the old event, which wakes up all senders waiting on it.
        """

        self._default_block_on_full: bool = False
        """Whether new receivers block senders when full, unless told otherwise.

        Only a `BroadcastChannel` sets it.
        """

        self._closed: bool = False
        """Whether the channel is closed."""

        self._latest: ChannelMessageT | None = None
        """The latest message sent to the channel."""

        self._auto_close_enabled: bool = auto_close
        """Whether to close the channel when all senders or all receivers are closed."""

        self.resend_latest: bool = resend_latest
        """Whether to resend the latest message to new receivers.

        When `True`, every time a new receiver is created with
        [`.new_receiver()`][frequenz.channels.Broadcast.new_receiver], it will
        automatically get sent the latest message on the channel.  This allows new
        receivers on slow streams to get the latest message as soon as they are created,
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

    async def aclose(self) -> None:
        """Close this channel.

        Any further attempts to [`send()`][frequenz.channels.Sender.send] data
        will raise a [`SenderError`][frequenz.channels.SenderError].

        Receivers will still be able to drain the pending items on their queues,
        but after that, subsequent
        [`receive()`][frequenz.channels.Receiver.receive] calls will return `None`
        immediately.
        """
        self._latest = None
        self._closed = True
        self._wake_senders()
        async with self._recv_cv:
            self._recv_cv.notify_all()

    def _wake_senders(self) -> None:
        """Wake up all senders waiting for blocking receivers to have room."""
        event, self._wake_senders_event = self._wake_senders_event, None
        if event is None:
            return
        try:
            event.set()
        except RuntimeError:
            # `set()` raises if the waiters' loop is closed, and they can't be woken
            # up anyway.  All waiters of an event share one loop, so any other
            # `RuntimeError` is re-raised.
            loop = getattr(event, "_loop", None)
            if loop is None or not loop.is_closed():
                raise

    def _full_blocking_receivers(self) -> tuple[list[str], bool]:
        """Return the blocking receivers that are full.

        It returns only strings, so a sender waiting for room doesn't keep any
        receiver alive.

        Returns:
            The names of the blocking receivers whose buffer is full, and whether
                any of them logs a warning on overflow.
        """
        full: list[str] = []
        warn = False
        stale_refs = []
        # pylint: disable=protected-access
        for _hash, recv_ref in self._blocking_receivers.items():
            recv = recv_ref()
            if recv is None:
                stale_refs.append(_hash)
                continue
            if recv._is_full():
                full.append(str(recv))
                warn = warn or recv._warn_on_overflow
        # pylint: enable=protected-access
        for _hash in stale_refs:
            del self._blocking_receivers[_hash]
        return full, warn

    @deprecated("The close() method is deprecated, use aclose() instead")
    async def close(self) -> None:
        """Close the channel.

        Deprecated alias for [`.aclose()`][frequenz.channels.Broadcast.aclose].
        """
        return await self.aclose()

    def new_sender(self) -> BroadcastSender[ChannelMessageT]:
        """Return a new sender attached to this channel."""
        return BroadcastSender(self)

    def new_receiver(  # noqa: DOC502 (raised indirectly)
        self, *, name: str | None = None, limit: int = 50, warn_on_overflow: bool = True
    ) -> BroadcastReceiver[ChannelMessageT]:
        """Return a new receiver attached to this channel.

        Broadcast receivers have their own buffer, and when messages are not
        being consumed fast enough and the buffer fills up, old messages will
        get dropped just in this receiver.

        Args:
            name: A name to identify the receiver in the logs.
            limit: Number of messages the receiver can hold in its buffer.  It
                must be at least 1.
            warn_on_overflow: Whether to log a warning when the receiver's
                buffer is full and a message is dropped.

        Returns:
            A new receiver attached to this channel.

        Raises:
            ValueError: If `limit` is smaller than 1.
        """
        return self._new_receiver(
            name=name,
            limit=limit,
            warn_on_overflow=warn_on_overflow,
            block_on_full=self._default_block_on_full,
        )

    def _new_receiver(  # noqa: DOC502 (raised indirectly)
        self,
        *,
        name: str | None,
        limit: int,
        warn_on_overflow: bool,
        block_on_full: bool,
    ) -> BroadcastReceiver[ChannelMessageT]:
        """Return a new receiver attached to this channel.

        Args:
            name: A name to identify the receiver in the logs.
            limit: Number of messages the receiver can hold in its buffer.
            warn_on_overflow: Whether to log a warning when the receiver's
                buffer is full and a message is dropped, or a sender has to wait.
            block_on_full: Whether senders wait for the receiver to have room
                when its buffer is full, instead of dropping its oldest message.

        Returns:
            A new receiver attached to this channel.

        Raises:
            ValueError: If `limit` is smaller than 1.
        """
        recv: BroadcastReceiver[ChannelMessageT] = BroadcastReceiver(
            self,
            name=name,
            limit=limit,
            warn_on_overflow=warn_on_overflow,
            block_on_full=block_on_full,
        )
        self._receivers[hash(recv)] = weakref.ref(recv)
        if block_on_full:
            self._blocking_receivers[hash(recv)] = weakref.ref(recv)
        if self.resend_latest and self._latest is not None:
            recv._enqueue(self._latest)  # pylint: disable=protected-access
        return recv

    def __str__(self) -> str:
        """Return a string representation of this channel."""
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


_T = TypeVar("_T")


class BroadcastSender(CloneableSubscribableSender[_T]):
    """A sender to send messages to the broadcast channel.

    Should not be created directly, but through the
    [`.clone()`][frequenz.channels.BroadcastSender.clone]
    method of an existing sender.
    """

    def __init__(self, channel: Broadcast[_T], /) -> None:
        """Initialize this sender.

        Args:
            channel: A reference to the broadcast channel this sender belongs to.
        """
        self._channel: Broadcast[_T] = channel
        """The broadcast channel this sender belongs to."""

        self._closed: bool = False
        """Whether this sender is closed."""

        self._channel._sender_count += 1

    @property
    def sender_count(self) -> int:
        """The number of open senders attached to this sender's channel."""
        return self._channel._sender_count  # pylint: disable=protected-access

    @override
    async def send(self, message: _T, /) -> None:  # noqa: DOC503 (raised indirectly)
        """Send a message to all broadcast receivers.

        If a receiver created with `block_on_full=True` has a full buffer, this
        waits until all such receivers have room, and then gives the message to all
        receivers at once.  If it is cancelled while waiting, for example by
        [`asyncio.timeout()`][asyncio.timeout], no receiver gets the message.

        Args:
            message: The message to be broadcast.

        Raises:
            SenderError: If the underlying channel was closed, also while
                waiting.  A
                [`ChannelClosedError`][frequenz.channels.ChannelClosedError] is set
                as the cause.
            SenderClosedError: If this sender was closed, also while waiting.
        """
        self._check_open()
        # pylint: disable=protected-access
        if self._channel._blocking_receivers:
            await self._wait_for_room()
        stale_refs = []
        for _hash, recv_ref in self._channel._receivers.items():
            recv = recv_ref()
            if recv is None:
                stale_refs.append(_hash)
                continue
            recv._enqueue(message)
        for _hash in stale_refs:
            del self._channel._receivers[_hash]
        if self._channel._auto_close_enabled and len(self._channel._receivers) == 0:
            await self._channel.aclose()
            raise SenderError("The channel was closed", self) from ChannelClosedError(
                self._channel
            )
        self._channel._latest = message
        async with self._channel._recv_cv:
            self._channel._recv_cv.notify_all()
        # pylint: enable=protected-access

    async def _wait_for_room(self) -> None:  # noqa: DOC502 (raised indirectly)
        """Wait until no blocking receiver of the channel is full.

        Raises:
            SenderError: If the underlying channel was closed while waiting.
            SenderClosedError: If this sender was closed while waiting.
        """
        # pylint: disable=protected-access
        channel = self._channel
        full, warn = channel._full_blocking_receivers()
        if not full:
            return
        _logger.log(
            logging.WARNING if warn else logging.DEBUG,
            "Broadcast sender [%s] is blocked until receivers have room: %s",
            self,
            ", ".join(full),
        )
        while full:
            if channel._wake_senders_event is None:
                channel._wake_senders_event = Event()
            await channel._wake_senders_event.wait()
            self._check_open()
            full, _ = channel._full_blocking_receivers()
        _logger.log(
            logging.INFO if warn else logging.DEBUG,
            "Broadcast sender [%s] is no longer blocked, all receivers have room",
            self,
        )
        # pylint: enable=protected-access

    @override
    async def aclose(self) -> None:
        """Close this sender.

        After a sender is closed, it can no longer be used to send messages. Any
        attempt to send a message through a closed sender will raise a
        [`SenderClosedError`][frequenz.channels.SenderClosedError], also if it is
        waiting for receivers to have room.
        """
        if self._closed:
            return
        self._closed = True
        self._channel._sender_count -= 1
        self._channel._wake_senders()  # pylint: disable=protected-access

        if (
            self._channel._sender_count == 0  # pylint: disable=protected-access
            and self._channel._auto_close_enabled  # pylint: disable=protected-access
        ):
            await self._channel.aclose()

    def _check_open(self) -> None:
        """Check that this sender and its channel are open.

        Raises:
            SenderError: If the underlying channel is closed.
            SenderClosedError: If this sender is closed.
        """
        if self._closed:
            raise SenderClosedError(self)
        if self._channel._closed:  # pylint: disable=protected-access
            raise SenderError("The channel was closed", self) from ChannelClosedError(
                self._channel
            )

    @override
    def clone(self) -> BroadcastSender[_T]:
        """Return a clone of this sender."""
        return BroadcastSender(self._channel)

    @override
    def subscribe(  # noqa: DOC502 (raised indirectly)
        self,
        name: str | None = None,
        limit: int = 50,
        warn_on_overflow: bool = True,
        *,
        block_on_full: bool | CHANNEL_DEFAULT = CHANNEL_DEFAULT,
    ) -> BroadcastReceiver[_T]:
        """Return a new receiver attached to this sender's channel.

        Args:
            name: A name to identify the receiver in the logs.
            limit: Number of messages the receiver can hold in its buffer.  It must
                be at least 1.
            warn_on_overflow: Whether to log a warning when the receiver's buffer is
                full and a message is dropped, or when a sender has to wait for the
                receiver to have room.
            block_on_full: Whether senders wait for this receiver to have room when
                its buffer is full, instead of dropping its oldest message.  With
                [`CHANNEL_DEFAULT`][frequenz.channels.CHANNEL_DEFAULT], the
                `block_on_full` value the
                [`BroadcastChannel`][frequenz.channels.BroadcastChannel] was created
                with is used.

        Returns:
            A new receiver attached to this sender's channel.

        Raises:
            SenderError: If the underlying channel is closed.
            SenderClosedError: If this sender is closed.
            ValueError: If `limit` is smaller than 1.
        """
        self._check_open()
        if block_on_full is CHANNEL_DEFAULT:
            # Go through the public method, which subclasses of the deprecated
            # `Broadcast` might override.
            return self._channel.new_receiver(
                name=name, limit=limit, warn_on_overflow=warn_on_overflow
            )
        return self._channel._new_receiver(  # pylint: disable=protected-access
            name=name,
            limit=limit,
            warn_on_overflow=warn_on_overflow,
            block_on_full=block_on_full,
        )

    def __str__(self) -> str:
        """Return a string representation of this sender."""
        return f"{self._channel}:{type(self).__name__}"

    def __repr__(self) -> str:
        """Return a string representation of this sender."""
        return f"{type(self).__name__}({self._channel!r})"


class BroadcastReceiver(Receiver[_T]):
    """A receiver to receive messages from the broadcast channel.

    Should not be created directly, but through the
    [`BroadcastSender.subscribe()`][frequenz.channels.BroadcastSender.subscribe]
    method of an existing sender.
    """

    def __init__(
        self,
        channel: Broadcast[_T],
        /,
        *,
        name: str | None,
        limit: int,
        warn_on_overflow: bool,
        block_on_full: bool = False,
    ) -> None:
        """Initialize this receiver.

        Broadcast receivers have their own buffer, and when messages are not
        being consumed fast enough and the buffer fills up, old messages will
        get dropped just in this receiver.

        Args:
            channel: A reference to the [`Broadcast`][frequenz.channels.Broadcast]
                channel that this receiver belongs to.
            name: A name to identify the receiver in the logs. If `None` an
                `id(self)`-based name will be used.  This is only for debugging
                purposes, it will be shown in the string representation of the
                receiver.
            limit: Number of messages the receiver can hold in its buffer.  It
                must be at least 1.
            warn_on_overflow: Whether to log a warning when the receiver's
                buffer is full and a message is dropped, or a sender has to wait.
            block_on_full: Whether senders wait for this receiver to have room
                when its buffer is full, instead of dropping its oldest message.

        Raises:
            ValueError: If `limit` is smaller than 1.
        """
        if limit < 1:
            raise ValueError(f"The receiver's limit must be at least 1, not {limit}")

        self._warn_on_overflow: bool = warn_on_overflow

        self._name: str = name if name is not None else f"{id(self):_}"
        """The name to identify the receiver.

        Only used for debugging purposes.
        """

        self._channel: Broadcast[_T] = channel
        """The broadcast channel that this receiver belongs to."""

        self._q: deque[_T] = deque(maxlen=limit)
        """The receiver's internal message queue."""

        self._closed: bool = False
        """Whether the receiver is closed."""

        self._block_on_full: bool = block_on_full
        """Whether senders wait for this receiver to have room when it is full."""

    def _is_full(self) -> bool:
        """Return whether this receiver's buffer is full."""
        return len(self._q) == self._q.maxlen

    def _enqueue(self, message: _T, /) -> None:
        """Put a message into this receiver's queue.

        To be called by broadcast senders.  If the receiver's queue is already
        full, drop the oldest message to make room for the incoming message, and
        log a warning.

        Args:
            message: The message to be sent.
        """
        if len(self._q) == self._q.maxlen:
            self._q.popleft()
            if self._warn_on_overflow:
                _logger.warning(
                    "Broadcast receiver [%s] is full. Oldest message was dropped.",
                    self,
                )
        self._q.append(message)

    def __len__(self) -> int:
        """Return the number of unconsumed messages in the broadcast receiver.

        Returns:
            Number of items in the receiver's internal queue.
        """
        return len(self._q)

    @override
    async def ready(self) -> bool:
        """Wait until the receiver is ready with a message or an error.

        Once a call to [`.ready()`][frequenz.channels.BroadcastReceiver.ready] has
        finished, the message should be read with a call to
        [`.consume()`][frequenz.channels.BroadcastReceiver.consume]
        ([`receive()`][frequenz.channels.Receiver.receive] or iterated over). The
        receiver will remain ready (this method will return immediately) until it is
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
            if self._channel._closed or self._closed:
                return False
            if self._channel._auto_close_enabled and self._channel._sender_count == 0:
                await self._channel.aclose()
                return False
            async with self._channel._recv_cv:
                await self._channel._recv_cv.wait()
        return True
        # pylint: enable=protected-access

    @override
    def consume(self) -> _T:
        """Return the latest message once the receiver is ready.

        [`ready()`][frequenz.channels.BroadcastReceiver.ready] must be called before each call to
        [`consume()`][frequenz.channels.BroadcastReceiver.consume].

        Returns:
            The next message that was received.

        Raises:
            ReceiverStoppedError: If there is some problem with the receiver.
        """
        if not self._q and self._channel._closed:  # pylint: disable=protected-access
            raise ReceiverStoppedError(self) from ChannelClosedError(self._channel)

        if self._closed:
            raise ReceiverStoppedError(self)

        assert self._q, "`consume()` must be preceded by a call to `ready()`"
        message = self._q.popleft()
        if self._block_on_full:
            self._channel._wake_senders()  # pylint: disable=protected-access
        return message

    @override
    def close(self) -> None:
        """Close the receiver.

        After calling this method, new messages will not be received.  Once the
        receiver's buffer is drained, trying to receive a message will raise a
        [`ReceiverStoppedError`][frequenz.channels.ReceiverStoppedError].
        """
        self._closed = True
        # pylint: disable=protected-access
        self._channel._receivers.pop(hash(self), None)
        if self._block_on_full:
            self._channel._blocking_receivers.pop(hash(self), None)
            self._channel._wake_senders()
        # pylint: enable=protected-access

    def __str__(self) -> str:
        """Return a string representation of this receiver."""
        return f"{self._channel}:{type(self).__name__}:{self._name}"

    def __repr__(self) -> str:
        """Return a string representation of this receiver."""
        limit = self._q.maxlen
        assert limit is not None
        return (
            f"{type(self).__name__}(name={self._name!r}, limit={limit!r}, "
            f"block_on_full={self._block_on_full!r}, "
            f"{self._channel!r}):<id={id(self)!r}, used={len(self._q)!r}>"
        )


class BroadcastChannel(
    tuple[BroadcastSender[ChannelMessageT], BroadcastReceiver[ChannelMessageT]]
):
    """A channel that delivers all messages to all receivers.

    # Description

    [`BroadcastChannel`][frequenz.channels.BroadcastChannel]s can have multiple
    [senders][frequenz.channels.BroadcastSender] and multiple
    [receivers][frequenz.channels.BroadcastReceiver]. Each message sent through
    any of the senders will be received by all receivers.

    <center>
    ```bob
    .---------. msg1                           msg1,msg2  .-----------.
    | Sender  +------.                        .---------->| Receiver  |
    '---------'      |      .----------.     |            '-----------'
                     +----->| Channel  +-----+
    .---------.      |      '----------'     |            .-----------.
    | Sender  +------'                       '----------->| Receiver  |
    '---------' msg2                           msg1,msg2  '-----------'
    ```
    </center>

    !!! Note inline end "Characteristics"

        * **Buffered:** Yes, with one buffer per receiver
        * **Buffer full policy:** Drop oldest message, or block senders
        * **Multiple receivers:** Yes
        * **Multiple senders:** Yes
        * **Thread-safe:** No

    This channel is buffered, and when messages are not being consumed fast
    enough and the buffer fills up, old messages will get dropped, unless the
    channel was created with `block_on_full=True`, see below.

    Each receiver has its own buffer, so messages will only be dropped for
    receivers that can't keep up with the senders, and not for the whole
    channel.

    Instantiating this class will create a new broadcast channel, and return an
    initial sender and a receiver.  Further senders and receivers can be created
    with the [`BroadcastSender.clone()`][frequenz.channels.BroadcastSender.clone],
    and
    [`BroadcastSender.subscribe()`][frequenz.channels.BroadcastSender.subscribe]
    methods respectively.

    When a sender or a receiver is not needed anymore, it should be closed with
    [`BroadcastSender.aclose()`][frequenz.channels.BroadcastSender.aclose] or
    [`BroadcastReceiver.close()`][frequenz.channels.BroadcastReceiver.close]. This will prevent
    further attempts to [`send()`][frequenz.channels.BroadcastSender.send] data,
    and will allow receivers to drain the pending items on their queues, but
    after that, subsequent [`receive()`][frequenz.channels.Receiver.receive] calls
    will raise a
    [`ReceiverStoppedError`][frequenz.channels.ReceiverStoppedError].

    When all senders of a channel are closed, all its receivers will be
    automatically closed, and vice versa.

    This channel is useful, for example, to implement a pub/sub pattern, where
    multiple consumers can subscribe to a channel to receive all messages.

    # Blocking senders

    When messages must not be lost, create the channel with `block_on_full=True`.
    Then, when a receiver's buffer is full,
    [`send()`][frequenz.channels.BroadcastSender.send] waits until every receiver
    that blocks senders has room for the message, and then gives it to all
    receivers at once.  This
    slows senders down to the pace of the slowest receiver, which is called
    backpressure.

    To limit how long a sender waits, use [`asyncio.timeout()`][asyncio.timeout].
    If `send()` is cancelled or times out while waiting, no receiver gets the
    message, and it isn't resent to new receivers either, as it would be with
    `resend_latest=True`.

    The setting is stored per receiver.  Receivers created with
    [`subscribe()`][frequenz.channels.BroadcastSender.subscribe] use the
    channel's `block_on_full` setting, unless they pass their own.  A receiver
    that can lose messages, for example one that only logs them, can pass
    `block_on_full=False`, so it never makes senders wait.

    When a sender starts waiting, it logs a warning, and when it stops waiting, an
    info message.  If none of the full receivers was created with
    `warn_on_overflow=True`, both are debug messages instead.

    Messages sent by awaiting one `send()` after another stay in order.
    Concurrent `send()` calls, even through the same sender, have no order: any of
    them can complete first.

    When a receiver that blocks senders consumes a message, every waiting sender
    wakes up and checks again all the receivers it waits for.  So many senders
    waiting on a channel with many such receivers do a lot of extra work.

    Warning:
        With `block_on_full=True`, a receiver that is not read stops all senders as
        soon as its buffer is full.  Close every receiver you don't need, including
        the initial one.  A receiver that is garbage-collected without being closed
        doesn't wake up a sender that is already waiting for it.  That sender keeps
        waiting until it is woken up for another reason, like another receiver
        reading a message, or until it is cancelled, for example by a timeout.

        Don't wait on `send()` from the task that reads the channel's only
        receiver: once the buffer is full, the task waits for itself forever.

    # Examples

    Example: Send a few numbers to a receiver
        This is a very simple example that sends a few numbers from a single sender to
        a single receiver.

        ```python
        import asyncio

        from frequenz.channels import BroadcastChannel, Sender


        async def send(sender: Sender[int]) -> None:
            for message in range(3):
                print(f"sending {message}")
                await sender.send(message)
            await sender.aclose()


        async def main() -> None:
            sender, receiver = BroadcastChannel[int](name="numbers")

            async with asyncio.TaskGroup() as task_group:
                task_group.create_task(send(sender))
                for _ in range(3):
                    message = await receiver.receive()
                    print(f"received {message}")
                    await asyncio.sleep(0.1)  # sleep (or work) with the data


        asyncio.run(main())
        ```

        The output should look something like (although the sending and received might
        appear more interleaved):

        ```
        sending 0
        sending 1
        sending 2
        received 0
        received 1
        received 2
        ```

    Example: Send a few number from multiple senders to multiple receivers
        This is a more complex example that sends a few numbers from multiple senders to
        multiple receivers, using a small buffer to force the senders to block.

        ```python show_lines="4:"
        # Workaround for https://github.com/frequenz-floss/frequenz-repo-config-python/issues/669
        # pylint: disable=too-many-lines

        import asyncio

        from frequenz.channels import BroadcastChannel, Receiver, ReceiverStoppedError, Sender


        async def send(name: str, sender: Sender[int], start: int, stop: int) -> None:
            for message in range(start, stop):
                print(f"{name} sending {message}")
                await sender.send(message)
            await sender.aclose()


        async def recv(name: str, receiver: Receiver[int]) -> None:
            try:
                async for message in receiver:
                    print(f"{name} received {message}")
                await asyncio.sleep(0.1)  # sleep (or work) with the data
            except ReceiverStoppedError:
                pass


        async def main() -> None:
            sender_1, receiver_1 = BroadcastChannel[int](name="numbers")
            sender_2 = sender_1.clone()
            receiver_2 = sender_1.subscribe()
            async with asyncio.TaskGroup() as task_group:
                task_group.create_task(send("sender_1", sender_1, 10, 13))
                task_group.create_task(send("sender_2", sender_2, 20, 22))
                task_group.create_task(recv("receiver_1", receiver_1))
                task_group.create_task(recv("receiver_2", receiver_2))


        asyncio.run(main())
        ```

        The output should look something like this(although the sending and received
        might appear interleaved in a different way):

        ```
        sender_1 sending 10
        sender_1 sending 11
        sender_1 sending 12
        sender_2 sending 20
        sender_2 sending 21
        receiver_1 received 10
        receiver_1 received 11
        receiver_1 received 12
        receiver_1 received 20
        receiver_1 received 21
        receiver_2 received 10
        receiver_2 received 11
        receiver_2 received 12
        receiver_2 received 20
        receiver_2 received 21
        ```

    Example: Make a fast sender wait for a slow receiver
        This example sends numbers faster than they are received.  With
        `block_on_full=True`, the sender waits for the receiver to have room instead
        of dropping messages.

        ```python show_lines="4:"
        # Workaround for https://github.com/frequenz-floss/frequenz-repo-config-python/issues/669
        # pylint: disable=too-many-lines

        import asyncio

        from frequenz.channels import BroadcastChannel, Receiver, Sender


        async def send(sender: Sender[int]) -> None:
            for message in range(4):
                await sender.send(message)
                print(f"sent {message}")
            await sender.aclose()


        async def receive(receiver: Receiver[int]) -> None:
            async for message in receiver:
                print(f"received {message}")
                await asyncio.sleep(0.1)  # sleep (or work) with the data


        async def main() -> None:
            sender, receiver = BroadcastChannel[int](
                name="numbers", limit=2, warn_on_overflow=False, block_on_full=True
            )

            async with asyncio.TaskGroup() as task_group:
                task_group.create_task(send(sender))
                task_group.create_task(receive(receiver))


        asyncio.run(main())
        ```

        The output should be:

        ```
        sent 0
        sent 1
        received 0
        sent 2
        received 1
        sent 3
        received 2
        received 3
        ```
    """

    def __new__(  # noqa: DOC502 (raised indirectly)
        cls,
        name: str,
        resend_latest: bool = False,
        limit: int = 50,
        warn_on_overflow: bool = True,
        *,
        block_on_full: bool = False,
    ) -> BroadcastChannel[ChannelMessageT]:
        """Create a new BroadcastChannel instance.

        Args:
            name: The name of the channel. This is for logging purposes, and it will be
                shown in the string representation of the channel.
            resend_latest: When True, every time a new receiver is created with
                [`Broadcast.new_receiver()`][frequenz.channels.Broadcast.new_receiver],
                the last message seen by the channel will be sent to the
                new receiver automatically. This allows new receivers on slow streams to
                get the latest message as soon as they are created, without having to
                wait for the next message on the channel to arrive.  It is safe to be
                set in data/reporting channels, but is not recommended for use in
                channels that stream control instructions.
            limit: Number of messages the receivers can hold in their buffers.  It
                must be at least 1.
            warn_on_overflow: Whether to log a warning when a receiver's buffer is full
                and a message is dropped, or when a sender has to wait for a receiver
                to have room.
            block_on_full: Whether senders wait for receivers to have room when their
                buffer is full, instead of dropping their oldest message.  It applies
                to the initial receiver and, by default, to receivers created with
                [`BroadcastSender.subscribe()`][frequenz.channels.BroadcastSender.subscribe].

        Returns:
            A new BroadcastChannel instance that can be destructured into an initial
                sender and receiver.

        Raises:
            ValueError: If `limit` is smaller than 1.
        """
        # Broadcast is deprecated, but it is an implementation detail of this
        # class, so users shouldn't be warned about it.
        with ignoring_deprecations():
            channel = Broadcast[ChannelMessageT](
                name=name, resend_latest=resend_latest, auto_close=True
            )
        channel._default_block_on_full = (  # pylint: disable=protected-access
            block_on_full
        )
        return tuple.__new__(
            cls,
            (
                channel.new_sender(),
                channel.new_receiver(
                    name=f"{name}_receiver",
                    limit=limit,
                    warn_on_overflow=warn_on_overflow,
                ),
            ),
        )
