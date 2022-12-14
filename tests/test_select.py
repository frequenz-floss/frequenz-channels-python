# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the Select implementation."""

import asyncio
from typing import List

from frequenz.channels import Anycast, Sender
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
    select = Select(
        ch1=chan1.new_receiver(),
        ch2=chan2.new_receiver(),
        ch3=chan3.new_receiver(),
    )

    # only check for messages from all iterators but `ch3`.
    # it ensures iterators are not blocking channels in case they
    # are not being read from.
    results: List[int] = []
    while await select.ready():
        if item := select.ch1:
            if val := item.inner:
                results.append(val)
            else:
                results.append(-1)
        elif item := select.ch2:
            if val := item.inner:
                results.append(val)
            else:
                results.append(-2)
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
    got_err = False
    try:
        item = select.unknown_channel
    except KeyError:
        got_err = True
    assert got_err
