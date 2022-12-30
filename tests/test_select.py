# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the Select implementation."""

import asyncio
from typing import List

from frequenz.channels import Anycast, ReceiverStoppedError, Sender
from frequenz.channels.util import Select


async def test_select() -> None:
    """Ensure select receives messages in order."""
    chan1 = Anycast[int]()
    chan2 = Anycast[int]()
    chan3 = Anycast[int]()

    async def send(ch1: Sender[int], ch2: Sender[int], ch3: Sender[int]) -> None:
        for ctr in range(5):
            await ch1.send(ctr + 1)
            await ch2.send(ctr + 101)
            await ch3.send(ctr + 201)
        await chan1.close()
        await ch2.send(1000)
        await chan2.close()
        await chan3.close()

    senders = asyncio.create_task(
        send(chan1.new_sender(), chan2.new_sender(), chan3.new_sender()),
    )

    recv1 = chan1.new_receiver()
    recv2 = chan2.new_receiver()
    recv3 = chan3.new_receiver()

    select = Select(recv1, recv2, recv3)

    # only check for messages from all iterators but `ch3`.
    # it ensures iterators are not blocking channels in case they
    # are not being read from.
    results: List[int] = []
    async for ready_set in select.ready():
        if recv1 in ready_set:
            try:
                msg = recv1.consume()
            except ReceiverStoppedError:
                results.append(-1)
            else:
                results.append(msg)

        if recv2 in ready_set:
            try:
                msg = recv2.consume()
            except ReceiverStoppedError:
                results.append(-2)
            else:
                results.append(msg)

        if recv3 in ready_set:
            try:
                _ = recv3.consume()
            except ReceiverStoppedError:
                pass
    await senders

    expected_results = [
        1,
        101,
        2,
        102,
        3,
        103,
        4,
        104,
        5,
        105,
        -1,  # marks end of messages from channel 1
        1000,
        -2,  # marks end of messages from channel 2
    ]
    assert results == expected_results
