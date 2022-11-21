# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the MergeNamed implementation."""

import asyncio
from typing import List, Tuple

from frequenz.channels import Anycast, MergeNamed, Sender


async def test_mergenamed() -> None:
    """Ensure MergeNamed receives messages in order."""
    chan1 = Anycast[int]()
    chan2 = Anycast[int]()

    async def send(ch1: Sender[int], ch2: Sender[int]) -> None:
        for ctr in range(5):
            await ch1.send(ctr + 1)
            await ch2.send(ctr + 101)
        await chan1.close()
        await ch2.send(1000)
        await chan2.close()

    senders = asyncio.create_task(send(chan1.get_sender(), chan2.get_sender()))
    recvs = {"chan1": chan1.get_receiver(), "chan2": chan2.get_receiver()}

    merge = MergeNamed(**recvs)
    results: List[Tuple[str, int]] = []
    async for item in merge:
        results.append(item)
    await senders
    for ctr in range(5):
        idx = ctr * 2
        # It is hard to get messages from multiple channels in the same order,
        # so we use a `set` to check the next N messages are the same, in any
        # order, where N is the number of channels.  This only works in this
        # example because the `send` method sends values in immeidate
        # succession.
        assert set((results[idx : idx + 2])) == {
            ("chan1", ctr + 1),
            ("chan2", ctr + 101),
        }
    assert results[-1] == ("chan2", 1000)
