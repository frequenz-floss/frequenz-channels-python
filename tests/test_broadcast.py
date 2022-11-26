# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the Broadcast implementation."""

import asyncio
from typing import Tuple

import pytest

from frequenz.channels import (
    Broadcast,
    ChannelClosedError,
    Receiver,
    Sender,
    SenderError,
)


async def test_broadcast() -> None:
    """Ensure sent messages are received by all receivers."""

    bcast: Broadcast[int] = Broadcast("meter_5")

    num_receivers = 5
    num_senders = 5
    expected_sum = num_senders * num_receivers * num_receivers * (num_receivers + 1) / 2

    # a list of `num_receivers` elements, where each element with get
    # incremented by values the corrosponding receiver receives.  Once the run
    # finishes, we will check if their sum equals `expected_sum`.
    recv_trackers = [0] * num_receivers

    async def send_msg(chan: Sender[int]) -> None:
        # send one message for each receiver
        for ctr in range(num_receivers):
            await chan.send(ctr + 1)

    async def update_tracker_on_receive(receiver_id: int, chan: Receiver[int]) -> None:
        while True:
            try:
                msg = await chan.receive()
            except ChannelClosedError:
                return
            recv_trackers[receiver_id] += msg

    receivers = []
    for ctr in range(num_receivers):
        receivers.append(update_tracker_on_receive(ctr, bcast.new_receiver()))

    receivers_runs = asyncio.gather(*receivers)
    senders = []
    for ctr in range(num_senders):
        senders.append(send_msg(bcast.new_sender()))

    await asyncio.gather(*senders)
    await bcast.close()
    await receivers_runs

    actual_sum = 0
    for ctr in recv_trackers:
        ## ensure all receivers have got messages
        assert ctr > 0
        actual_sum += ctr
    assert actual_sum == expected_sum


async def test_broadcast_after_close() -> None:
    """Ensure closed channels can't get new messages."""
    bcast: Broadcast[int] = Broadcast("meter_5")

    receiver = bcast.new_receiver()
    sender = bcast.new_sender()

    await bcast.close()

    with pytest.raises(SenderError):
        await sender.send(5)
    with pytest.raises(ChannelClosedError):
        await receiver.receive()


async def test_broadcast_overflow() -> None:
    """Ensure messages sent to full broadcast receivers get dropped."""
    bcast: Broadcast[int] = Broadcast("meter_5")

    big_recv_size = 10
    small_recv_size = int(big_recv_size / 2)
    sender = bcast.new_sender()

    big_receiver = bcast.new_receiver("named-recv", big_recv_size)
    small_receiver = bcast.new_receiver(None, small_recv_size)

    async def drain_receivers() -> Tuple[int, int]:
        big_sum = 0
        small_sum = 0
        while len(big_receiver) > 0:
            msg = await big_receiver.receive()
            assert msg is not None
            big_sum += msg

        while len(small_receiver) > 0:
            msg = await small_receiver.receive()
            assert msg is not None
            small_sum += msg
        return (big_sum, small_sum)

    # we send `big_recv_size` messages first, then drain the receivers, then
    # send `big_recv_size` messages again.  Then get the sum.
    total_messages = 2 * big_recv_size
    big_sum = 0
    small_sum = 0
    for ctr in range(total_messages):
        await sender.send(ctr + 1)
        if (ctr + 1) % big_recv_size == 0:
            big, small = await drain_receivers()
            big_sum += big
            small_sum += small

    assert big_sum == total_messages * (total_messages + 1) / 2

    # small_sum should be sum of `small_recv_size+1 .. big_recv_size`, and
    # big_sum should be the numbers from `big_recv_size+small_recv_size+1` to
    # `2 * big_recv_size`.
    assert small_sum == (
        small_recv_size * (small_recv_size + big_recv_size + 1) / 2
    ) + (
        small_recv_size
        * (2 * big_recv_size + (small_recv_size + big_recv_size + 1))
        / 2
    )


async def test_broadcast_resend_latest() -> None:
    """Check if new receivers get the latest value when resend_latest is set."""
    bcast: Broadcast[int] = Broadcast("new_recv_test", resend_latest=True)

    sender = bcast.new_sender()
    old_recv = bcast.new_receiver()
    for val in range(0, 10):
        await sender.send(val)
    new_recv = bcast.new_receiver()

    await sender.send(100)

    assert await old_recv.receive() == 0
    assert await new_recv.receive() == 9
    assert await new_recv.receive() == 100


async def test_broadcast_no_resend_latest() -> None:
    """Ensure new receivers don't get the latest value when resend_latest isn't set."""
    bcast: Broadcast[int] = Broadcast("new_recv_test", resend_latest=False)

    sender = bcast.new_sender()
    old_recv = bcast.new_receiver()
    for val in range(0, 10):
        await sender.send(val)
    new_recv = bcast.new_receiver()

    await sender.send(100)

    assert await old_recv.receive() == 0
    assert await new_recv.receive() == 100


async def test_broadcast_peek() -> None:
    """Ensure we are able to peek into broadcast channels."""
    bcast: Broadcast[int] = Broadcast("peek-test")
    receiver = bcast.new_receiver()
    peekable = receiver.into_peekable()
    sender = bcast.new_sender()

    with pytest.raises(EOFError):
        await receiver.receive()

    assert peekable.peek() is None

    for val in range(0, 10):
        await sender.send(val)

    assert peekable.peek() == 9
    assert peekable.peek() == 9

    await sender.send(20)

    assert peekable.peek() == 20

    await bcast.close()
    assert peekable.peek() is None


async def test_broadcast_async_iterator() -> None:
    """Check that the broadcast receiver works as an async iterator."""
    bcast: Broadcast[int] = Broadcast("iter_test")

    sender = bcast.new_sender()
    receiver = bcast.new_receiver()

    async def send_values() -> None:
        for val in range(0, 10):
            await sender.send(val)
        await bcast.close()

    sender_task = asyncio.create_task(send_values())

    received = []
    async for recv in receiver:
        received.append(recv)

    assert received == list(range(0, 10))

    await sender_task


async def test_broadcast_map() -> None:
    """Ensure map runs on all incoming messages."""
    chan = Broadcast[int]("input-chan")
    sender = chan.new_sender()

    # transform int receiver into bool receiver.
    receiver: Receiver[bool] = chan.new_receiver().map(lambda num: num > 10)

    await sender.send(8)
    await sender.send(12)

    assert (await receiver.receive()) is False
    assert (await receiver.receive()) is True


async def test_broadcast_receiver_drop() -> None:
    """Ensure deleted receivers get cleaned up."""
    chan = Broadcast[int]("input-chan")
    sender = chan.new_sender()

    receiver1 = chan.new_receiver()
    receiver2 = chan.new_receiver()

    await sender.send(10)

    assert 10 == await receiver1.receive()
    assert 10 == await receiver2.receive()

    assert len(chan.receivers) == 2

    del receiver2

    await sender.send(20)

    assert len(chan.receivers) == 1
