# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Integration tests for the merge implementation."""

import asyncio

import pytest

from frequenz.channels import Anycast, Sender, merge


@pytest.mark.integration
async def test_merge() -> None:
    """Ensure merge() receives messages in order."""
    chan1 = Anycast[int](name="chan1")
    chan2 = Anycast[int](name="chan2")

    async def send(ch1: Sender[int], ch2: Sender[int]) -> None:
        for ctr in range(5):
            await ch1.send(ctr + 1)
            await ch2.send(ctr + 101)
        await chan1.close()
        await ch2.send(1000)
        await chan2.close()

    senders = asyncio.create_task(send(chan1.new_sender(), chan2.new_sender()))

    results: list[int] = []
    async for item in merge(chan1.new_receiver(), chan2.new_receiver()):
        results.append(item)
    await senders
    for ctr in range(5):
        idx = ctr * 2
        # It is hard to get messages from multiple channels in the same order,
        # so we use a `set` to check the next N messages are the same, in any
        # order, where N is the number of channels.  This only works in this
        # example because the `send` method sends messages in immediate
        # succession.
        assert set(results[idx : idx + 2]) == {ctr + 1, ctr + 101}
    assert results[-1] == 1000
