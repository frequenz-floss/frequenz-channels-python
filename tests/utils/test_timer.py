# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for `channel.Timer`."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from frequenz.channels import Anycast, Sender
from frequenz.channels.util import Select, Timer

logger = logging.Logger(__name__)


async def test_timer() -> None:
    """Ensure Timer messages arrive on time."""

    @dataclass
    class _TestCase:
        count: int
        delta: float

    # if the fast test doesn't pass,  we'll switch to a slow test.
    test_cases = [
        _TestCase(count=10, delta=0.05),
        _TestCase(count=6, delta=0.2),
        _TestCase(count=6, delta=0.5),
    ]
    fail_count = 0
    for test_case in test_cases:
        start = datetime.now(timezone.utc)
        count = 0
        async for _ in Timer(test_case.delta):
            count += 1
            if count >= test_case.count:
                break
        actual_duration = (datetime.now(timezone.utc) - start).total_seconds()
        expected_duration = test_case.delta * test_case.count
        tolerance = expected_duration * 0.1

        assert actual_duration >= expected_duration
        if actual_duration <= expected_duration + tolerance:
            break
        logger.error(
            "%s failed :: actual_duration=%s > expected_duration=%s + tolerance=%s",
            test_case,
            actual_duration,
            expected_duration,
            tolerance,
        )
        fail_count += 1
    assert fail_count < len(test_cases)


# pylint: disable=too-many-locals
async def test_timer_reset() -> None:
    """Ensure timer resets function as expected."""
    chan1 = Anycast[int]()

    count = 4
    reset_delta = 0.1
    timer_delta = 0.3

    async def send(ch1: Sender[int]) -> None:
        for ctr in range(count):
            await asyncio.sleep(reset_delta)
            await ch1.send(ctr)

    senders = asyncio.create_task(send(chan1.new_sender()))

    timer = Timer(timer_delta)
    msg_recv = chan1.new_receiver()

    select = Select(msg_recv, timer)

    start_ts = datetime.now(timezone.utc)
    stop_ts: Optional[datetime] = None
    async for ready_set in select.ready():
        if msg_recv in ready_set:
            _ = msg_recv.consume()  # We need to consume the message
            timer.reset()
        if timer in ready_set:
            stop_ts = timer.consume()
            break

    assert stop_ts is not None
    actual_duration = (stop_ts - start_ts).total_seconds()
    expected_duration = reset_delta * count + timer_delta
    tolerance = expected_duration * 0.1
    assert actual_duration >= expected_duration
    assert actual_duration <= expected_duration + tolerance

    await senders
