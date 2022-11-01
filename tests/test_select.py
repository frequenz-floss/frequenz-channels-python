# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the Select implementation."""

import asyncio
from asyncio import Queue
from typing import List, Optional

from frequenz.channels import Anycast, Select, Sender


class AsyncIterable:
    """Example AsyncIterator class"""

    def __init__(self) -> None:
        self.queue: "Queue[int]" = Queue()
        self.done = False

    def __aiter__(self) -> "AsyncIterable":
        return self

    async def __anext__(self) -> Optional[int]:
        if not self.queue.empty():
            return self.queue.get_nowait()
        if self.done:
            raise StopAsyncIteration
        msg = await self.queue.get()
        return msg

    async def add(self, msg: int) -> bool:
        """Adds object to iterator"""
        await self.queue.put(msg)

        return True


async def test_select() -> None:
    """Ensure select receives messages in order."""
    chan1 = Anycast[int]()
    chan2 = Anycast[int]()
    chan3 = Anycast[int]()

    async def send(
        ch1: Sender[int], ch2: Sender[int], ch3: Sender[int], queue: AsyncIterable
    ) -> None:
        for ctr in range(5):
            await ch1.send(ctr + 1)
            await ch2.send(ctr + 101)
            await ch3.send(ctr + 201)
            await queue.add(ctr + 301)
        await chan1.close()
        await ch2.send(1000)
        await chan2.close()
        await chan3.close()
        queue.done = True

    queue = AsyncIterable()

    senders = asyncio.create_task(
        send(chan1.get_sender(), chan2.get_sender(), chan3.get_sender(), queue),
    )
    select = Select(
        ch1=chan1.get_receiver(),
        ch2=chan2.get_receiver(),
        ch3=chan3.get_receiver(),
        ch4=queue,
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
        elif item := select.ch4:
            if val := item.inner:
                results.append(val)
            else:
                results.append(-4)
    await senders

    expected_results = [
        1,
        101,
        301,
        2,
        102,
        302,
        3,
        103,
        303,
        4,
        104,
        304,
        5,
        105,
        305,
        -1,  # marks end of messages from channel 1
        1000,
        -4,  # marks end of messages from channel 4
        -2,  # marks end of messages from channel 2
    ]
    assert results == expected_results
    got_err = False
    try:
        item = select.unknown_channel
    except KeyError:
        got_err = True
    assert got_err
