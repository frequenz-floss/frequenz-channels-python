# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""Integration tests for the timer."""


import asyncio
from datetime import timedelta

import async_solipsism
import pytest

from frequenz.channels.timer import SkipMissedAndDrift, Timer


@pytest.mark.integration
async def test_timer_timeout_reset(
    event_loop: async_solipsism.EventLoop,  # pylint: disable=redefined-outer-name
) -> None:
    """Test that the receiving is properly adjusted after a reset."""

    async def timer_wait(timer: Timer) -> None:
        await timer.receive()

    async with asyncio.timeout(2.0):
        async with asyncio.TaskGroup() as task_group:
            timer = Timer(timedelta(seconds=1.0), SkipMissedAndDrift())
            start_time = event_loop.time()
            task_group.create_task(timer_wait(timer))
            await asyncio.sleep(0.5)
            timer.reset()

    run_time = event_loop.time() - start_time
    assert run_time >= 1.5
