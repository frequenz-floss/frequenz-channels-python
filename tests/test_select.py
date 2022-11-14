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
            print(f"SEND: ch1: {ctr+101}")
            await ch1.send(ctr + 101)
            print(f"SEND: ch2: {ctr+201}")
            await ch2.send(ctr + 201)
            print(f"SEND: ch3: {ctr+301}")
            await ch3.send(ctr + 301)
            print(f"SEND: ch4: {ctr+401}")
            await queue.add(ctr + 401)
        print(f"CLOSE: ch1")
        await chan1.close()
        print(f"SEND: ch2: 1000")
        await ch2.send(1000)
        print(f"CLOSE: ch2")
        await chan2.close()
        print(f"CLOSE: ch3")
        print(f"DONE: ch4")
        await chan3.close()
        queue.done = True

    queue = AsyncIterable()
    ch1 = chan1.get_receiver()
    ch2 = chan2.get_receiver()
    ch3 = chan3.get_receiver()

    senders = asyncio.create_task(
        send(chan1.get_sender(), chan2.get_sender(), chan3.get_sender(), queue),
    )
    select = Select(
        ch1=ch1,
        ch2=ch2,
        ch3=ch3,
        ch4=queue,
    )

    # only check for messages from all iterators but `ch3`.
    # it ensures iterators are not blocking channels in case they
    # are not being read from.
    results: List[int] = []
    async for selected in select.ready():
        print(f"selected: {selected.name=} {selected.result=}")
        if selected.origin is ch1:
            if val := selected.result:
                results.append(val)
            else:
                results.append(-1)
        elif selected.origin is ch2:
            if val := selected.result:
                results.append(val)
            else:
                results.append(-2)
        elif selected.origin is queue: 
            if val := selected.result:
                results.append(val)
            else:
                results.append(-4)
    await senders

    expected_results = [
        101,
        201,
        401,
        102,
        202,
        402,
        103,
        203,
        403,
        104,
        204,
        404,
        105,
        205,
        405,
        -1,  # marks end of messages from channel 1
        1000,
        -4,  # marks end of messages from channel 4
        -2,  # marks end of messages from channel 2
    ]
    assert results == expected_results
