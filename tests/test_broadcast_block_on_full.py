# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for broadcast channels with `block_on_full=True`."""

import asyncio
import gc
import logging

import pytest
from frequenz.core.warnings import asserting_no_deprecations

from frequenz.channels import (
    CHANNEL_DEFAULT,
    Broadcast,
    BroadcastChannel,
    BroadcastReceiver,
    BroadcastSender,
    ChannelClosedError,
    SenderClosedError,
    SenderError,
    SenderWouldBlockError,
    TransientSenderError,
)


async def _settle() -> None:
    """Let all ready tasks run until they block again."""
    for _ in range(10):
        await asyncio.sleep(0)


def _drain(receiver: BroadcastReceiver[int]) -> list[int]:
    """Return all messages in a receiver's buffer, without waiting."""
    messages = []
    while len(receiver) > 0:
        messages.append(receiver.consume())
    return messages


async def _start_send(sender: BroadcastSender[int], message: int) -> asyncio.Task[None]:
    """Start sending a message in a task, and let it run until it blocks."""
    task = asyncio.create_task(sender.send(message))
    await _settle()
    return task


async def _start_send_with(
    sender: BroadcastSender[int], message: int, *, block_on_full: bool
) -> asyncio.Task[None]:
    """Start sending a message with a `block_on_full` override in a task."""
    task = asyncio.create_task(sender.send(message, block_on_full=block_on_full))
    await _settle()
    return task


async def test_default_drops_oldest() -> None:
    """Ensure a channel created without `block_on_full` still drops messages."""
    sender, receiver = BroadcastChannel[int](
        name="test", limit=2, warn_on_overflow=False
    )

    for message in range(4):
        await sender.send(message)

    assert _drain(receiver) == [2, 3]


async def test_send_waits_for_room() -> None:
    """Ensure a send to a full receiver waits until a message is received."""
    sender, receiver = BroadcastChannel[int](name="test", limit=2, block_on_full=True)
    await sender.send(1)
    await sender.send(2)

    task = await _start_send(sender, 3)
    assert not task.done()
    assert len(receiver) == 2

    assert await receiver.receive() == 1
    await _settle()
    assert task.done()
    await task
    assert _drain(receiver) == [2, 3]


async def test_ready_without_consume_doesnt_wake() -> None:
    """Ensure a receiver only makes room when a message is consumed."""
    sender, receiver = BroadcastChannel[int](name="test", limit=1, block_on_full=True)
    await sender.send(1)

    task = await _start_send(sender, 2)
    assert await receiver.ready()
    await _settle()
    assert not task.done()

    assert receiver.consume() == 1
    await _settle()
    assert task.done()
    await task
    assert _drain(receiver) == [2]


async def test_all_or_nothing() -> None:
    """Ensure no receiver gets a message until all blocking receivers have room."""
    sender, receiver_1 = BroadcastChannel[int](name="test", limit=1, block_on_full=True)
    receiver_2 = sender.subscribe(limit=2)
    await sender.send(1)
    assert _drain(receiver_2) == [1]

    task = await _start_send(sender, 2)
    assert not task.done()
    assert len(receiver_2) == 0

    assert receiver_1.consume() == 1
    await _settle()
    assert task.done()
    await task
    assert _drain(receiver_1) == [2]
    assert _drain(receiver_2) == [2]


async def test_lossy_receiver_waits_too() -> None:
    """Ensure a lossy receiver gets nothing while a blocking receiver is full."""
    sender, blocking = BroadcastChannel[int](
        name="test", resend_latest=True, limit=1, block_on_full=True
    )
    lossy = sender.subscribe(limit=1, block_on_full=False, warn_on_overflow=False)
    await sender.send(1)

    task = await _start_send(sender, 2)
    assert not task.done()
    assert len(lossy) == 1

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert _drain(lossy) == [1]
    assert _drain(blocking) == [1]
    late = sender.subscribe(block_on_full=False)
    assert _drain(late) == [1]


async def test_cancelled_send_delivers_nothing() -> None:
    """Ensure a send that times out gives the message to no receiver."""
    sender, receiver_1 = BroadcastChannel[int](
        name="test", resend_latest=True, limit=1, block_on_full=True
    )
    receiver_2 = sender.subscribe(limit=5)
    await sender.send(1)

    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.01):
            await sender.send(2)

    assert _drain(receiver_1) == [1]
    assert _drain(receiver_2) == [1]
    receiver_3 = sender.subscribe()
    assert _drain(receiver_3) == [1]

    await sender.send(3)
    assert _drain(receiver_1) == [3]
    assert _drain(receiver_2) == [3]
    assert _drain(receiver_3) == [3]


async def test_subscribe_inherits_block_on_full() -> None:
    """Ensure `subscribe()` uses the channel's setting unless told otherwise."""
    sender, receiver = BroadcastChannel[int](name="test", block_on_full=True)
    receiver.close()

    inherited = sender.subscribe(limit=1)
    explicit = sender.subscribe(limit=1, block_on_full=CHANNEL_DEFAULT)
    lossy = sender.subscribe(limit=1, block_on_full=False, warn_on_overflow=False)
    assert "block_on_full=CHANNEL_DEFAULT" in repr(inherited)
    assert "block_on_full=CHANNEL_DEFAULT" in repr(explicit)
    assert "block_on_full=False" in repr(lossy)

    await sender.send(1)
    task = await _start_send(sender, 2)
    assert not task.done()

    assert inherited.consume() == 1
    await _settle()
    assert not task.done()

    assert explicit.consume() == 1
    await _settle()
    assert task.done()
    await task
    assert _drain(lossy) == [2]


async def test_subscribe_uses_overridden_new_receiver() -> None:
    """Ensure `subscribe()` without `block_on_full` uses `new_receiver()`."""

    class CustomBroadcast(Broadcast[int]):
        """A broadcast channel with custom receivers."""

        def new_receiver(
            self,
            *,
            name: str | None = None,
            limit: int = 50,
            warn_on_overflow: bool = True,
        ) -> BroadcastReceiver[int]:
            return super().new_receiver(
                name="custom", limit=2, warn_on_overflow=warn_on_overflow
            )

    sender = CustomBroadcast(name="test").new_sender()

    assert "name='custom', limit=2" in repr(sender.subscribe())
    assert "name='custom', limit=2" in repr(
        sender.subscribe(block_on_full=CHANNEL_DEFAULT)
    )
    assert "name='custom'" not in repr(sender.subscribe(block_on_full=True))


async def test_lossy_receiver_never_blocks() -> None:
    """Ensure a lossy receiver on a blocking channel drops messages instead."""
    sender, blocking = BroadcastChannel[int](name="test", limit=5, block_on_full=True)
    lossy = sender.subscribe(limit=1, block_on_full=False, warn_on_overflow=False)

    for message in range(3):
        await sender.send(message)

    assert _drain(lossy) == [2]
    assert _drain(blocking) == [0, 1, 2]


async def test_blocking_receiver_on_lossy_channel() -> None:
    """Ensure a blocking receiver makes senders of a lossy channel wait."""
    sender, lossy = BroadcastChannel[int](name="test", limit=1, warn_on_overflow=False)
    blocking = sender.subscribe(limit=1, block_on_full=True)
    await sender.send(1)

    task = await _start_send(sender, 2)
    assert not task.done()

    assert blocking.consume() == 1
    await _settle()
    assert task.done()
    await task
    assert _drain(lossy) == [2]
    assert _drain(blocking) == [2]


async def test_resend_latest_fills_new_receiver() -> None:
    """Ensure the message resent to a new receiver counts towards its buffer."""
    sender, receiver = BroadcastChannel[int](
        name="test", resend_latest=True, limit=1, block_on_full=True
    )
    await sender.send(1)
    assert receiver.consume() == 1

    task = await _start_send(sender, 2)
    await task

    new_receiver = sender.subscribe(limit=1)
    assert len(new_receiver) == 1
    assert receiver.consume() == 2

    task = await _start_send(sender, 3)
    assert not task.done()

    assert new_receiver.consume() == 2
    await _settle()
    assert task.done()
    await task


async def test_receiver_subscribed_while_waiting() -> None:
    """Ensure a send waits for receivers subscribed after it started waiting."""
    sender, receiver = BroadcastChannel[int](
        name="test", resend_latest=True, limit=1, block_on_full=True
    )
    await sender.send(1)

    task = await _start_send(sender, 2)
    new_receiver = sender.subscribe(limit=1)
    assert len(new_receiver) == 1

    assert receiver.consume() == 1
    await _settle()
    assert not task.done()

    assert new_receiver.consume() == 1
    await _settle()
    assert task.done()
    await task
    assert _drain(receiver) == [2]
    assert _drain(new_receiver) == [2]


async def test_closing_full_receiver_wakes_sender() -> None:
    """Ensure closing the full receiver lets a waiting send finish."""
    sender, receiver_1 = BroadcastChannel[int](name="test", limit=1, block_on_full=True)
    receiver_2 = sender.subscribe(limit=5)
    await sender.send(1)

    task = await _start_send(sender, 2)
    assert not task.done()

    receiver_1.close()
    await _settle()
    assert task.done()
    await task
    assert _drain(receiver_2) == [1, 2]


async def test_dropped_receiver_doesnt_block_new_sends() -> None:
    """Ensure a receiver dropped without closing doesn't block later sends."""
    sender, receiver_1 = BroadcastChannel[int](name="test", limit=1, block_on_full=True)
    receiver_2 = sender.subscribe(limit=5)
    await sender.send(1)

    del receiver_1
    gc.collect()

    await sender.send(2)
    assert _drain(receiver_2) == [1, 2]


async def test_closing_last_receiver_while_waiting() -> None:
    """Ensure a waiting send fails like any other if all receivers are closed."""
    sender, receiver = BroadcastChannel[int](name="test", limit=1, block_on_full=True)
    await sender.send(1)

    task = await _start_send(sender, 2)
    receiver.close()
    await _settle()

    assert task.done()
    with pytest.raises(SenderError) as excinfo:
        await task
    assert isinstance(excinfo.value.__cause__, ChannelClosedError)


async def test_closing_other_sender_keeps_waiting() -> None:
    """Ensure closing another sender doesn't stop a waiting send."""
    sender_1, receiver = BroadcastChannel[int](name="test", limit=1, block_on_full=True)
    sender_2 = sender_1.clone()
    await sender_1.send(1)

    task = await _start_send(sender_1, 2)
    await sender_2.aclose()
    await _settle()
    assert not task.done()

    assert receiver.consume() == 1
    await _settle()
    assert task.done()
    await task
    assert _drain(receiver) == [2]


async def test_closing_waiting_sender() -> None:
    """Ensure closing a waiting sender stops its send, and closes the channel."""
    sender, receiver = BroadcastChannel[int](name="test", limit=1, block_on_full=True)
    await sender.send(1)

    task = await _start_send(sender, 2)
    await sender.aclose()
    await _settle()

    assert task.done()
    with pytest.raises(SenderClosedError):
        await task
    assert _drain(receiver) == [1]
    assert not await receiver.ready()


async def test_closing_one_of_two_waiting_senders() -> None:
    """Ensure closing one waiting sender leaves the other one waiting."""
    sender_1, receiver = BroadcastChannel[int](name="test", limit=1, block_on_full=True)
    sender_2 = sender_1.clone()
    await sender_1.send(1)

    task_1 = await _start_send(sender_1, 2)
    task_2 = await _start_send(sender_2, 3)
    await sender_1.aclose()
    await _settle()

    assert task_1.done()
    with pytest.raises(SenderClosedError):
        await task_1
    assert not task_2.done()

    assert receiver.consume() == 1
    await _settle()
    assert task_2.done()
    await task_2
    assert _drain(receiver) == [3]


async def test_closing_channel_wakes_sender() -> None:
    """Ensure closing the channel stops a waiting send."""
    channel = Broadcast[int](name="test")
    sender = channel.new_sender()
    receiver = sender.subscribe(limit=1, block_on_full=True)
    await sender.send(1)

    task = await _start_send(sender, 2)
    await channel.aclose()
    await _settle()

    assert task.done()
    with pytest.raises(SenderError) as excinfo:
        await task
    assert isinstance(excinfo.value.__cause__, ChannelClosedError)
    assert _drain(receiver) == [1]


async def test_several_waiting_senders() -> None:
    """Ensure several waiting senders all deliver, each in order."""
    sender, receiver = BroadcastChannel[int](
        name="test", limit=2, warn_on_overflow=False, block_on_full=True
    )

    async def send_all(sender: BroadcastSender[int], messages: range) -> None:
        for message in messages:
            await sender.send(message)

    tasks = [
        asyncio.create_task(send_all(sender.clone(), range(start, start + 5)))
        for start in (0, 100, 200)
    ]
    received: list[int] = []
    while len(received) < 15:
        received.append(await receiver.receive())
        await _settle()
    await asyncio.gather(*tasks)

    assert sorted(received) == sorted(
        [*range(0, 5), *range(100, 105), *range(200, 205)]
    )
    for start in (0, 100, 200):
        assert [m for m in received if start <= m < start + 100] == list(
            range(start, start + 5)
        )


async def test_cancelling_one_of_several_waiting_senders() -> None:
    """Ensure cancelling one waiting send doesn't stop the others."""
    sender, receiver = BroadcastChannel[int](
        name="test", limit=1, warn_on_overflow=False, block_on_full=True
    )
    await sender.send(0)

    task_1 = await _start_send(sender, 1)
    task_2 = await _start_send(sender, 2)
    task_3 = await _start_send(sender, 3)
    task_2.cancel()
    await _settle()
    assert task_2.cancelled()

    received = [receiver.consume()]
    for _ in range(2):
        await _settle()
        received.append(receiver.consume())
    await asyncio.gather(task_1, task_3)
    assert sorted(received) == [0, 1, 3]


async def test_logging(caplog: pytest.LogCaptureFixture) -> None:
    """Ensure waiting is logged as a warning when the receiver warns on overflow."""
    caplog.set_level(logging.DEBUG, logger="frequenz.channels._broadcast")
    sender, receiver = BroadcastChannel[int](name="test", limit=1, block_on_full=True)
    await sender.send(1)

    task = await _start_send(sender, 2)
    assert receiver.consume() == 1
    await _settle()
    assert task.done()
    await task

    assert [(r.levelno, r.getMessage()) for r in caplog.records] == [
        (
            logging.WARNING,
            "Broadcast sender [Broadcast:test:BroadcastSender] is blocked until "
            "receivers have room: Broadcast:test:BroadcastReceiver:test_receiver",
        ),
        (
            logging.INFO,
            "Broadcast sender [Broadcast:test:BroadcastSender] is no longer blocked, "
            "all receivers have room",
        ),
    ]


async def test_logging_without_warn_on_overflow(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Ensure waiting is logged at debug level when the receiver doesn't warn."""
    caplog.set_level(logging.DEBUG, logger="frequenz.channels._broadcast")
    sender, receiver = BroadcastChannel[int](
        name="test", limit=1, warn_on_overflow=False, block_on_full=True
    )
    await sender.send(1)

    task = await _start_send(sender, 2)
    assert receiver.consume() == 1
    await _settle()
    assert task.done()
    await task

    assert [r.levelno for r in caplog.records] == [logging.DEBUG, logging.DEBUG]


@pytest.mark.parametrize("action", ["close", "consume"])
def test_wake_up_after_loop_closed(action: str) -> None:
    """Ensure a receiver can be used after the loop of a waiting sender is closed."""
    sender, receiver = BroadcastChannel[int](name="test", limit=1, block_on_full=True)

    async def start_waiting_send() -> None:
        await sender.send(1)
        await _start_send(sender, 2)

    loop = asyncio.new_event_loop()
    loop.run_until_complete(start_waiting_send())
    loop.close()

    if action == "close":
        receiver.close()
    else:
        assert receiver.consume() == 1
    # pylint: disable-next=protected-access
    assert sender._channel._wake_senders_event is None


async def test_does_not_warn() -> None:
    """Ensure creating a blocking `BroadcastChannel` emits no deprecation warning."""
    with asserting_no_deprecations():
        _ = BroadcastChannel[int](name="test", block_on_full=True)


async def test_send_override_true_waits_for_inheriting_receivers() -> None:
    """Ensure `send(block_on_full=True)` waits for receivers using the default."""
    sender, inheriting = BroadcastChannel[int](
        name="test", limit=1, warn_on_overflow=False
    )
    await sender.send(1)

    task = await _start_send_with(sender, 2, block_on_full=True)
    assert not task.done()
    assert _drain(inheriting) == [1]
    await _settle()
    assert task.done()
    await task
    assert _drain(inheriting) == [2]


async def test_send_override_true_forgets_dropped_receivers() -> None:
    """Ensure `send(block_on_full=True)` forgets dropped blocking receivers."""
    sender, receiver = BroadcastChannel[int](name="test", limit=5)
    dropped = sender.subscribe(block_on_full=True)
    del dropped
    gc.collect()

    await sender.send(1, block_on_full=True)

    # pylint: disable=protected-access
    assert len(sender._channel._receivers) == 1
    assert not sender._channel._blocking_receivers
    # pylint: enable=protected-access
    assert _drain(receiver) == [1]


async def test_send_override_true_skips_explicitly_lossy_receivers() -> None:
    """Ensure `send(block_on_full=True)` doesn't wait for explicitly lossy receivers."""
    sender, inheriting = BroadcastChannel[int](
        name="test", limit=5, warn_on_overflow=False
    )
    lossy = sender.subscribe(limit=1, warn_on_overflow=False, block_on_full=False)
    await sender.send(1)

    await sender.send(2, block_on_full=True)
    assert _drain(lossy) == [2]
    assert _drain(inheriting) == [1, 2]


async def test_send_override_true_woken_by_inheriting_receiver_close() -> None:
    """Ensure closing an inheriting receiver wakes `send(block_on_full=True)`."""
    sender, inheriting = BroadcastChannel[int](
        name="test", limit=1, warn_on_overflow=False
    )
    other = sender.subscribe(limit=5)
    await sender.send(1)

    task = await _start_send_with(sender, 2, block_on_full=True)
    assert not task.done()
    inheriting.close()
    await _settle()
    assert task.done()
    await task
    assert _drain(other) == [1, 2]


async def test_send_override_false_drops_on_inheriting_receivers() -> None:
    """Ensure `send(block_on_full=False)` never waits for inheriting receivers."""
    sender, inheriting = BroadcastChannel[int](
        name="test", limit=1, warn_on_overflow=False, block_on_full=True
    )
    await sender.send(1)

    await sender.send(2, block_on_full=False)
    assert _drain(inheriting) == [2]


async def test_send_override_false_raises_for_explicitly_blocking() -> None:
    """Ensure `send(block_on_full=False)` raises if an explicit blocker is full."""
    sender, inheriting = BroadcastChannel[int](
        name="test", resend_latest=True, limit=1, warn_on_overflow=False
    )
    blocking_1 = sender.subscribe(limit=1, block_on_full=True)
    blocking_2 = sender.subscribe(limit=5, block_on_full=True)
    await sender.send(1)

    with pytest.raises(SenderWouldBlockError) as excinfo:
        await sender.send(2, block_on_full=False)
    error = excinfo.value
    assert isinstance(error, TransientSenderError)
    assert error.sender is sender
    assert error.full_receivers == 1
    assert error.blocking_receivers == 2
    assert str(error) == (
        "Sender Broadcast:test:BroadcastSender would block: 1 of 2 receivers "
        "created with block_on_full=True are full"
    )

    assert _drain(inheriting) == [1]
    assert _drain(blocking_2) == [1]
    assert _drain(sender.subscribe()) == [1]

    assert blocking_1.consume() == 1
    await sender.send(3, block_on_full=False)
    assert _drain(inheriting) == [3]
    assert _drain(blocking_1) == [3]
    assert _drain(blocking_2) == [3]
