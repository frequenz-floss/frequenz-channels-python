# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the periodic timer."""

from __future__ import annotations

import asyncio
import enum
from collections.abc import Iterator
from datetime import timedelta

import async_solipsism
import pytest

from frequenz.channels.util import PeriodicTimer, SkipMissedAndDrift, TriggerAllMissed


# Setting 'autouse' has no effect as this method replaces the event loop for all tests in the file.
@pytest.fixture()
def event_loop() -> Iterator[async_solipsism.EventLoop]:
    """Replace the loop with one that doesn't interact with the outside world."""
    loop = async_solipsism.EventLoop()
    yield loop
    loop.close()


async def test_contruction() -> None:
    """TODO."""
    timer = PeriodicTimer(timedelta(seconds=1.0))
    assert timer.interval == timedelta(seconds=1.0)
    assert isinstance(timer.missed_tick_policy, TriggerAllMissed)
    assert timer.loop is asyncio.get_running_loop()
    assert timer.is_running is True


async def test_contruction_auto_start() -> None:
    """TODO."""
    policy = TriggerAllMissed()
    timer = PeriodicTimer(
        timedelta(seconds=5.0),
        auto_start=False,
        missed_tick_policy=policy,
        loop=None,
    )
    assert timer.interval == timedelta(seconds=5.0)
    assert timer.missed_tick_policy is policy
    assert timer.loop is asyncio.get_running_loop()
    assert timer.is_running is False


async def test_autostart(
    event_loop: async_solipsism.EventLoop,  # pylint: disable=redefined-outer-name
) -> None:
    """TODO."""
    timer = PeriodicTimer(timedelta(seconds=1.0))

    # We sleep some time, less than the interval, and then receive from the
    # timer, since it was automatically started at time 0, it should trigger at
    # time 1.0 without any drift
    await asyncio.sleep(0.5)
    drift = await timer.receive()
    assert drift == pytest.approx(timedelta(seconds=0.0))
    assert event_loop.time() == pytest.approx(1.0)


class _StartMethod(enum.Enum):
    RESET = enum.auto()
    RECEIVE = enum.auto()
    READY = enum.auto()
    ASYNC_ITERATOR = enum.auto()


@pytest.mark.parametrize("start_method", list(_StartMethod))
async def test_no_autostart(
    start_method: _StartMethod,
    event_loop: async_solipsism.EventLoop,  # pylint: disable=redefined-outer-name
) -> None:
    """TODO."""
    timer = PeriodicTimer(
        timedelta(seconds=1.0),
        auto_start=False,
    )

    # We sleep some time, less than the interval, and then start the timer and
    # receive from it, since it wasn't automatically started, it should trigger
    # shifted by the sleep time (without any drift)
    await asyncio.sleep(0.5)
    drift: timedelta | None = None
    if start_method == _StartMethod.RESET:
        timer.reset()
        drift = await timer.receive()
    elif start_method == _StartMethod.RECEIVE:
        drift = await timer.receive()
    elif start_method == _StartMethod.READY:
        assert await timer.ready() is True
        drift = timer.consume()
    elif start_method == _StartMethod.ASYNC_ITERATOR:
        async for _drift in timer:
            drift = _drift
            break
    else:
        assert False, f"Unknown start method {start_method}"

    assert drift == pytest.approx(timedelta(seconds=0.0))
    assert event_loop.time() == pytest.approx(1.5)


async def test_trigger_all(
    event_loop: async_solipsism.EventLoop,  # pylint: disable=redefined-outer-name
) -> None:
    """TODO."""
    interval = 1.0
    timer = PeriodicTimer(timedelta(seconds=interval))

    # We let the first tick be triggered on time
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval)
    assert drift == pytest.approx(timedelta(seconds=0.0))

    # Now we let the time pass interval plus a bit more, so we should get
    # a drift, but the next tick should be triggered still at a multiple of the
    # interval because we are using TRIGGER_ALL.
    await asyncio.sleep(interval + 0.1)
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 2 + 0.1)
    assert drift == pytest.approx(timedelta(seconds=0.1))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 3)
    assert drift == pytest.approx(timedelta(seconds=0.0))

    # Now we let the time pass by two times the interval, so we should get
    # a drift of a whole interval and then next tick should be triggered
    # immediately with no drift, because we are still at an interval boundary.
    await asyncio.sleep(2 * interval)
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 5)
    assert drift == pytest.approx(timedelta(seconds=interval))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 5)
    assert drift == pytest.approx(timedelta(seconds=0.0))

    # Finally we let the time pass by 5 times the interval plus some extra
    # delay (even when the tolerance should be irrelevant for this mode),
    # so we should catch up for the 4 missed ticks (the timer should trigger
    # immediately), with the drift of each trigger lowering. The last trigger
    # should have no drift once it catches up.
    extra_delay = 0.1
    await asyncio.sleep(5 * interval + extra_delay)
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 10 + extra_delay)
    assert drift == pytest.approx(timedelta(seconds=interval * 4 + extra_delay))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 10 + extra_delay)
    assert drift == pytest.approx(timedelta(seconds=interval * 3 + extra_delay))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 10 + extra_delay)
    assert drift == pytest.approx(timedelta(seconds=interval * 2 + extra_delay))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 10 + extra_delay)
    assert drift == pytest.approx(timedelta(seconds=interval * 1 + extra_delay))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 10 + extra_delay)
    assert drift == pytest.approx(timedelta(seconds=interval * 0 + extra_delay))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 11)
    assert drift == pytest.approx(timedelta(seconds=0.0))


async def test_skip_and_drift(
    event_loop: async_solipsism.EventLoop,  # pylint: disable=redefined-outer-name
) -> None:
    """TODO."""
    interval = 1.0
    tolerance = 0.1
    timer = PeriodicTimer(
        timedelta(seconds=interval),
        missed_tick_policy=SkipMissedAndDrift(
            delay_tolerance=timedelta(seconds=tolerance)
        ),
    )

    # We let the first tick be triggered on time
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval)
    assert drift == timedelta(seconds=0.0)

    # Now we let the time pass by the interval plus the tolerance so the drift
    # should be the tolerance and the next tick should be triggered still at
    # a multiple of the interval.
    await asyncio.sleep(interval + tolerance)
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 2 + tolerance)
    assert drift == pytest.approx(timedelta(seconds=tolerance))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 3)
    assert drift == pytest.approx(timedelta(seconds=0.0))

    # Now we let the time pass the interval plus two times the tolerance. Now
    # the timer should start to drift, and the next tick should be triggered at
    # a multiple of the interval plus the shift of two times the tolerance.
    await asyncio.sleep(interval + tolerance * 2)
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 4 + tolerance * 2)
    assert drift == pytest.approx(timedelta(seconds=tolerance * 2))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 5 + tolerance * 2)
    assert drift == pytest.approx(timedelta(seconds=0.0))

    # Now we let the time pass by two times the interval, so we should missed
    # one tick (the tick at time = 6 + tolerance * 2) and the next tick should
    # still be triggered at a multiple of the interval plus the shift of two
    # times the tolerance because the current trigger time was still aligned
    # to the shifted interval.
    await asyncio.sleep(2 * interval)
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 7 + tolerance * 2)
    assert drift == pytest.approx(timedelta(seconds=interval))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 8 + tolerance * 2)
    assert drift == pytest.approx(timedelta(seconds=0.0))

    # Finally we let the time pass by 5 times the interval plus a tiny bit more
    # than the tolerance, so we should missed 4 ticks (the ticks at times 9+,
    # 10+, 11+ and 12+). The current trigger is also delayed more than the
    # tolerance, so the next tick should accumulate the drift again.
    await asyncio.sleep(5 * interval + tolerance + 0.001)
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 13 + tolerance * 3 + 0.001)
    assert drift == pytest.approx(timedelta(seconds=interval * 4 + tolerance + 0.001))
    drift = await timer.receive()
    assert event_loop.time() == pytest.approx(interval * 14 + tolerance * 3 + 0.001)
    assert drift == pytest.approx(timedelta(seconds=0.0))
