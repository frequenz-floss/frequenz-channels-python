# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""Integration tests for Select function.

These tests are actually a bit in the middle between unit and integration, because we
are using a fake loop to make the tests faster, but we are still testing more than one
class at a time.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

import async_solipsism
import pytest

from frequenz.channels import (
    Receiver,
    ReceiverStoppedError,
    Selected,
    UnhandledSelectedError,
    select,
    selected_from,
)
from frequenz.channels.event import Event


@pytest.mark.integration
class TestSelect:
    """Tests for the select function."""

    recv1: Event
    recv2: Event
    recv3: Event
    loop: async_solipsism.EventLoop

    @pytest.fixture(autouse=True)
    def event_loop(
        self, request: pytest.FixtureRequest
    ) -> Iterator[async_solipsism.EventLoop]:
        """Replace the loop with one that doesn't interact with the outside world."""
        loop = async_solipsism.EventLoop()
        request.cls.loop = loop
        yield loop
        loop.close()

    @pytest.fixture()
    async def start_run_ordered_sequence(self) -> AsyncIterator[asyncio.Task[None]]:
        """Start the run_ordered_sequence method and wait for it to finish.

        Yields:
            The task running the run_ordered_sequence method.
        """
        sequence_task = asyncio.create_task(self.run_ordered_sequence())
        yield sequence_task
        await sequence_task

    def setup_method(self) -> None:
        """Set up the test."""
        self.recv1 = Event(name="recv1")
        self.recv2 = Event(name="recv2")
        self.recv3 = Event(name="recv3")

    def assert_received_from(
        self,
        selected: Selected[Any],
        receiver: Receiver[None],
        *,
        at_time: float,
        expected_pending_tasks: int = -2,
    ) -> None:
        """Assert that the selected event was received from the given receiver.

        It also asserts that:

        * The receiver didn't raise an exception.
        * The receiver wasn't stopped.
        * The select loop is still running.
        * It happened at the given time.

        Args:
            selected: The selected event.
            receiver: The receiver from which the event was received.
            at_time: The time at which the event was received.
            expected_pending_tasks: Check that a number of tasks are pending.  If the
                number is negative, a > check is performed with the absolute value.  If
                it is 0, no check is performed.
        """
        assert selected_from(selected, receiver)
        assert selected.message is None
        assert selected.exception is None
        assert not selected.was_stopped
        if expected_pending_tasks > 0:
            assert len(asyncio.all_tasks(self.loop)) == expected_pending_tasks
        elif expected_pending_tasks < 0:
            assert len(asyncio.all_tasks(self.loop)) > expected_pending_tasks
        assert self.loop.time() == at_time

    def assert_receiver_stopped(
        self,
        selected: Selected[Any],
        receiver: Receiver[None],
        *,
        at_time: float,
        expected_pending_tasks: int = -2,
    ) -> None:
        """Assert that the selected event came from a stopped receiver.

        It also asserts that:

        * The amount of pending tasks is as expected.
        * It happened at the given time.

        Args:
            selected: The selected event.
            receiver: The receiver from which the event was received.
            at_time: The time at which the event was received.
            expected_pending_tasks: Check that a number of tasks are pending.  If the
                number is negative, a > check is performed with the absolute value.  If
                it is 0, no check is performed.
        """
        assert selected_from(selected, receiver)
        assert selected.was_stopped
        assert isinstance(selected.exception, ReceiverStoppedError)
        assert selected.exception.receiver is receiver
        if expected_pending_tasks > 0:
            assert len(asyncio.all_tasks(self.loop)) == expected_pending_tasks
        elif expected_pending_tasks < 0:
            assert len(asyncio.all_tasks(self.loop)) > expected_pending_tasks
        assert self.loop.time() == at_time

    # We use the loop time (and the sleeps in the run_ordered_sequence method) mainly to
    # ensure we are processing the events in the correct order and we are really
    # following the sequence of events we expect.

    async def run_ordered_sequence(self) -> None:
        """Run the sequence of events to be tested."""
        print("time = 0")
        self.recv1.set()
        await asyncio.sleep(1)

        print("time = 1")
        self.recv2.set()
        await asyncio.sleep(1)

        print("time = 2")
        self.recv3.set()
        await asyncio.sleep(1)

        print("time = 3")
        self.recv1.set()
        await asyncio.sleep(1)

        print("time = 4")
        self.recv1.set()
        await asyncio.sleep(1)

        print("time = 5")
        self.recv3.set()
        await asyncio.sleep(1)

        print("time = 6")
        self.recv2.set()
        await asyncio.sleep(1)

        print("time = 7")
        self.recv1.stop()
        await asyncio.sleep(1)

        print("time = 8")
        self.recv2.set()
        await asyncio.sleep(1)

        print("time = 9")
        self.recv3.stop()
        await asyncio.sleep(1)

        print("time = 10")
        self.recv2.set()
        await asyncio.sleep(1)

        print("time = 11")
        self.recv2.stop()

    # pylint: disable=redefined-outer-name
    async def test_select_receives_in_order(
        self,
        start_run_ordered_sequence: asyncio.Task[  # pylint: disable=unused-argument
            None
        ],
    ) -> None:
        """Test that the select loop receives events in the correct order."""
        select_iter = select(self.recv1, self.recv2, self.recv3)

        selected = await anext(select_iter)
        self.assert_received_from(selected, self.recv1, at_time=0)

        selected = await anext(select_iter)
        self.assert_received_from(selected, self.recv2, at_time=1)

        selected = await anext(select_iter)
        self.assert_received_from(selected, self.recv3, at_time=2)

        selected = await anext(select_iter)
        self.assert_received_from(selected, self.recv1, at_time=3)

        selected = await anext(select_iter)
        self.assert_received_from(selected, self.recv1, at_time=4)

        selected = await anext(select_iter)
        self.assert_received_from(selected, self.recv3, at_time=5)

        selected = await anext(select_iter)
        self.assert_received_from(selected, self.recv2, at_time=6)

        selected = await anext(select_iter)
        self.assert_receiver_stopped(selected, self.recv1, at_time=7)

        selected = await anext(select_iter)
        self.assert_received_from(selected, self.recv2, at_time=8)

        selected = await anext(select_iter)
        self.assert_receiver_stopped(selected, self.recv3, at_time=9)

        selected = await anext(select_iter)
        self.assert_received_from(selected, self.recv2, at_time=10)

        selected = await anext(select_iter)
        self.assert_receiver_stopped(
            selected, self.recv2, at_time=11, expected_pending_tasks=1
        )

        with pytest.raises(StopAsyncIteration):
            selected = await anext(select_iter)

        assert len(asyncio.all_tasks()) == 1  # Only the test task should be alive

    async def test_break(
        self,
        start_run_ordered_sequence: asyncio.Task[  # pylint: disable=unused-argument
            None
        ],
    ) -> None:
        """Test that break works."""
        selected: Selected[Any] | None = None
        async for selected in select(self.recv1, self.recv2, self.recv3):
            if selected_from(selected, self.recv1):
                continue
            if selected_from(selected, self.recv2):
                continue
            if selected_from(selected, self.recv3):
                break

        assert selected is not None
        self.assert_received_from(selected, self.recv3, at_time=2)

        async for selected in select(self.recv1, self.recv2, self.recv3):
            if selected_from(selected, self.recv1):
                continue
            if selected_from(selected, self.recv2):
                break
            if selected_from(selected, self.recv3):
                continue

        assert selected is not None
        self.assert_received_from(selected, self.recv2, at_time=6)

        async for selected in select(self.recv1, self.recv2, self.recv3):
            if selected_from(selected, self.recv1):
                continue
            if selected_from(selected, self.recv2):
                continue
            if selected_from(selected, self.recv3):
                break

        assert selected is not None
        self.assert_receiver_stopped(selected, self.recv3, at_time=9)

        assert self.recv1.is_stopped
        assert self.recv3.is_stopped

        async for selected in select(self.recv2):
            if selected_from(selected, self.recv2):
                continue

        self.assert_receiver_stopped(
            selected, self.recv2, at_time=11, expected_pending_tasks=1
        )

        assert len(asyncio.all_tasks()) == 1  # Only the test task should be alive

    async def test_missed_select_from(
        self,
        start_run_ordered_sequence: asyncio.Task[  # pylint: disable=unused-argument
            None
        ],
    ) -> None:
        """Test that a missed `select_from` is detected."""
        selected: Selected[Any] | None = None
        with pytest.raises(UnhandledSelectedError) as excinfo:
            async for selected in select(self.recv1, self.recv2, self.recv3):
                if selected_from(selected, self.recv1):
                    continue
                if selected_from(selected, self.recv2):
                    continue

            assert False, "Should not reach this point"

        assert selected is not None
        assert excinfo.value.selected is selected
        self.assert_received_from(
            selected, self.recv3, at_time=2, expected_pending_tasks=2
        )

        # The test task and the run_ordered_sequence tasks should still be alive
        assert len(asyncio.all_tasks()) == 2
        assert start_run_ordered_sequence in asyncio.all_tasks()

    @pytest.fixture()
    async def start_run_multiple_ready(self) -> AsyncIterator[asyncio.Task[None]]:
        """Start the run_multiple_ready method and wait for it to finish.

        Yields:
            The task running the run_multiple_ready method.
        """
        sequence_task = asyncio.create_task(self.run_multiple_ready())
        yield sequence_task
        await sequence_task

    async def run_multiple_ready(self) -> None:
        """Run a sequence of events with multiple receivers ready."""
        print("time = 0")
        self.recv1.set()
        self.recv2.set()
        self.recv3.set()
        await asyncio.sleep(1)

        print("time = 1")
        self.recv2.set()
        self.recv3.set()
        await asyncio.sleep(1)

        print("time = 2")
        self.recv1.set()
        self.recv3.set()
        await asyncio.sleep(1)

        print("time = 3")
        self.recv1.set()
        self.recv2.set()
        await asyncio.sleep(1)

        print("time = 4")

    async def test_multiple_ready(
        self,
        start_run_multiple_ready: asyncio.Task[None],  # pylint: disable=unused-argument
    ) -> None:
        """Test that multiple ready receivers are handled properly.

        Also test that the loop waits forever if there are no more receivers ready.
        """
        received: set[str] = set()
        last_time: float = self.loop.time()
        try:
            async with asyncio.timeout(15):
                async for selected in select(self.recv1, self.recv2, self.recv3):
                    now = self.loop.time()
                    if now != last_time:  # Only check when there was a jump in time
                        match now:
                            case 1:
                                assert received == {
                                    self.recv1.name,
                                    self.recv2.name,
                                    self.recv3.name,
                                }
                            case 2:
                                assert received == {
                                    self.recv2.name,
                                    self.recv3.name,
                                }
                            case 3:
                                assert received == {
                                    self.recv1.name,
                                    self.recv3.name,
                                }
                            # case 4 needs to be checked after the timeout, as there
                            # are no ready receivers after time == 3.
                            case _:
                                assert False, "Should not reach this point"
                        received.clear()
                        last_time = now

                    if selected_from(selected, self.recv1):
                        received.add(self.recv1.name)
                    elif selected_from(selected, self.recv2):
                        received.add(self.recv2.name)
                    elif selected_from(selected, self.recv3):
                        received.add(self.recv3.name)
                    else:
                        assert False, "Should not reach this point"
        except asyncio.TimeoutError:
            assert self.loop.time() == 15
            # This happened after time == 3, but the loop never resumes because
            # there is nothing ready, so we need to check it after the timeout.
            assert received == {
                self.recv1.name,
                self.recv2.name,
            }
        else:
            assert False, "Should have timed out"

        assert len(asyncio.all_tasks()) == 1  # The test task should still be alive

    def test_tasks_are_cleaned_up_with_break(self) -> None:
        """Test that the tasks are cleaned up properly.

        In this test we use a real event loop instead of relying what is provided by
        pytest to make absolutely sure that the tasks are cleaned up properly with
        a real loop.
        """
        loop = asyncio.new_event_loop()

        async def run() -> None:
            task = loop.create_task(self.run_multiple_ready())
            async for selected in select(self.recv1, self.recv2, self.recv3):
                if selected_from(selected, self.recv1):
                    continue
                if selected_from(selected, self.recv2):
                    continue
                if selected_from(selected, self.recv3):
                    break

            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            # The loop might take a few "yields" to process all pending tasks and ensure
            # the finalized of select() was called
            iterations = 0
            while len(asyncio.all_tasks(loop)) > 1 and iterations < 5:
                await asyncio.sleep(0)

            assert len(asyncio.all_tasks(loop)) == 1

        loop.run_until_complete(run())
