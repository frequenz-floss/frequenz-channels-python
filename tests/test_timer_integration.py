# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""Integration tests for the timer."""

import asyncio
from datetime import timedelta

import async_solipsism
import pytest

from frequenz.channels.timer import SkipMissedAndDrift, Timer


@pytest.fixture(autouse=True)
def event_loop_policy() -> async_solipsism.EventLoopPolicy:
    """Return an event loop policy that uses the async solipsism event loop."""
    return async_solipsism.EventLoopPolicy()


@pytest.mark.integration
@pytest.mark.asyncio(loop_scope="function")
async def test_timer_timeout_reset() -> None:
    """Test that the receiving is properly adjusted after a reset."""
    event_loop = asyncio.get_running_loop()

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
