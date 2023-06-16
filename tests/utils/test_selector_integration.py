# License: MIT
# Copyright © 2023 Frequenz Energy-as-a-Service GmbH

"""Integration tests for Selector class.

These tests are actually a bit in the middle between unit and integration, because we
are using a fake loop to make the tests faster, but we are still testing more than one
class at a time.
"""

import asyncio
from collections.abc import AsyncIterator, Iterator
from typing import Any

import async_solipsism
import pytest

from frequenz.channels import Receiver, ReceiverStoppedError
from frequenz.channels.util import (
    Event,
    Selected,
    Selector,
    UnhandledSelectedError,
    selected_from,
)


@pytest.mark.integration
class TestSelector:
    """Tests for the Selector class."""

    recv1: Event
    recv2: Event
    recv3: Event
    selector: Selector
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
        self.recv1 = Event("recv1")
        self.recv2 = Event("recv2")
        self.recv3 = Event("recv3")
        self.selector = Selector(self.recv1, self.recv2, self.recv3)

    def assert_received_from(
        self,
        selected: Selected[Any],
        receiver: Receiver[None],
        *,
        at_time: float,
        selector_stopped: bool = False,
    ) -> None:
        """Assert that the selected event was received from the given receiver.

        It also asserts that:

        * The receiver didn't raise an exception.
        * The receiver wasn't stopped.
        * The selector is still running.
        * It happened at the given time.

        Args:
            selected: The selected event.
            receiver: The receiver from which the event was received.
            at_time: The time at which the event was received.
            selector_stopped: Check if the selector is stopped or running.
        """
        assert selected_from(selected, receiver)
        assert selected.value is None
        assert selected.exception is None
        assert not selected.was_stopped()
        assert self.selector.is_stopped == selector_stopped
        assert self.loop.time() == at_time

    def assert_receiver_stopped(
        self,
        selected: Selected[Any],
        receiver: Receiver[None],
        *,
        at_time: float,
        selector_stopped: bool = False,
    ) -> None:
        """Assert that the selected event came from a stopped receiver.

        It also asserts that:

        * The selector is still running (if `selector_stopped` is `False`).
        * The selector is stopped (if `selector_stopped` is `True`).
        * It happened at the given time.

        Args:
            selected: The selected event.
            receiver: The receiver from which the event was received.
            at_time: The time at which the event was received.
            selector_stopped: Check if the selector is stopped or running.
        """
        assert selected_from(selected, receiver)
        assert selected.was_stopped()
        assert isinstance(selected.exception, ReceiverStoppedError)
        assert selected.exception.receiver is receiver
        assert self.selector.is_stopped == selector_stopped
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
    async def test_selector_receives_in_order(
        self,
        start_run_ordered_sequence: asyncio.Task[  # pylint: disable=unused-argument
            None
        ],
    ) -> None:
        """Test that the selector receives events in the correct order."""
        assert self.selector.is_stopped

        async with self.selector:
            selector_iter = aiter(self.selector)

            selected = await anext(selector_iter)
            self.assert_received_from(selected, self.recv1, at_time=0)

            selected = await anext(selector_iter)
            self.assert_received_from(selected, self.recv2, at_time=1)

            selected = await anext(selector_iter)
            self.assert_received_from(selected, self.recv3, at_time=2)

            selected = await anext(selector_iter)
            self.assert_received_from(selected, self.recv1, at_time=3)

            selected = await anext(selector_iter)
            self.assert_received_from(selected, self.recv1, at_time=4)

            selected = await anext(selector_iter)
            self.assert_received_from(selected, self.recv3, at_time=5)

            selected = await anext(selector_iter)
            self.assert_received_from(selected, self.recv2, at_time=6)

            selected = await anext(selector_iter)
            self.assert_receiver_stopped(selected, self.recv1, at_time=7)

            selected = await anext(selector_iter)
            self.assert_received_from(selected, self.recv2, at_time=8)

            selected = await anext(selector_iter)
            self.assert_receiver_stopped(selected, self.recv3, at_time=9)

            selected = await anext(selector_iter)
            self.assert_received_from(selected, self.recv2, at_time=10)

            selected = await anext(selector_iter)
            self.assert_receiver_stopped(
                selected, self.recv2, at_time=11, selector_stopped=True
            )

            with pytest.raises(StopAsyncIteration):
                selected = await anext(selector_iter)
            assert self.selector.is_stopped

        assert len(asyncio.all_tasks()) == 1  # Only the test task should be alive
        assert self.selector.is_stopped

    async def test_break(
        self,
        start_run_ordered_sequence: asyncio.Task[  # pylint: disable=unused-argument
            None
        ],
    ) -> None:
        """Test that break works."""
        assert self.selector.is_stopped

        async with self.selector:
            selected: Selected[Any] | None = None
            async for selected in self.selector:
                if selected_from(selected, self.recv1):
                    continue
                if selected_from(selected, self.recv2):
                    continue
                if selected_from(selected, self.recv3):
                    break

            assert selected is not None
            self.assert_received_from(selected, self.recv3, at_time=2)

            async for selected in self.selector:
                if selected_from(selected, self.recv1):
                    continue
                if selected_from(selected, self.recv2):
                    break
                if selected_from(selected, self.recv3):
                    continue

            assert selected is not None
            self.assert_received_from(selected, self.recv2, at_time=6)

            async for selected in self.selector:
                if selected_from(selected, self.recv1):
                    continue
                if selected_from(selected, self.recv2):
                    continue
                if selected_from(selected, self.recv3):
                    break

            assert selected is not None
            self.assert_receiver_stopped(selected, self.recv3, at_time=9)

            async for selected in self.selector:
                if selected_from(selected, self.recv1):
                    break
                if selected_from(selected, self.recv2):
                    continue
                if selected_from(selected, self.recv3):
                    break

            self.assert_receiver_stopped(
                selected, self.recv2, at_time=11, selector_stopped=True
            )

        assert len(asyncio.all_tasks()) == 1  # Only the test task should be alive
        assert self.selector.is_stopped

    async def test_missed_select_from(
        self,
        start_run_ordered_sequence: asyncio.Task[  # pylint: disable=unused-argument
            None
        ],
    ) -> None:
        """Test that a missed `select_from` is detected."""
        assert self.selector.is_stopped

        selected: Selected[Any] | None = None
        with pytest.raises(UnhandledSelectedError) as excinfo:
            async with self.selector:
                async for selected in self.selector:
                    if selected_from(selected, self.recv1):
                        continue
                    if selected_from(selected, self.recv2):
                        continue

                assert False, "Should not reach this point"

        assert selected is not None
        assert excinfo.value.selected is selected
        self.assert_received_from(
            selected, self.recv3, at_time=2, selector_stopped=True
        )

        # The test task and the run_ordered_sequence tasks should still be alive
        assert len(asyncio.all_tasks()) == 2
        assert start_run_ordered_sequence in asyncio.all_tasks()
        assert self.selector.is_stopped

    async def test_cancel(
        self,
        start_run_ordered_sequence: asyncio.Task[  # pylint: disable=unused-argument
            None
        ],
    ) -> None:
        """Test that cancel works."""
        assert self.selector.is_stopped

        received: list[str] = []
        async with self.selector:
            async for selected in self.selector:
                if self.loop.time() == 5:
                    self.selector.cancel()
                if selected_from(selected, self.recv1):
                    received.append("recv1")
                    continue
                if selected_from(selected, self.recv2):
                    received.append("recv2")
                    continue
                if selected_from(selected, self.recv3):
                    received.append("recv3")
                    continue

            assert received == ["recv1", "recv2", "recv3", "recv1", "recv1", "recv3"]
            assert self.selector.is_stopped

        # The test task and the run_ordered_sequence tasks should still be alive
        assert len(asyncio.all_tasks()) == 2
        assert start_run_ordered_sequence in asyncio.all_tasks()
        assert self.selector.is_stopped

    async def test_manual_start_stop(
        self,
        start_run_ordered_sequence: asyncio.Task[  # pylint: disable=unused-argument
            None
        ],
    ) -> None:
        """Test that cancel works."""
        assert self.selector.is_stopped

        received: list[str] = []

        self.selector.start()
        assert not self.selector.is_stopped

        async for selected in self.selector:
            if self.loop.time() == 5:
                await self.selector.stop()
            if selected_from(selected, self.recv1):
                received.append("recv1")
                continue
            if selected_from(selected, self.recv2):
                received.append("recv2")
                continue
            if selected_from(selected, self.recv3):
                received.append("recv3")
                continue

        assert received == ["recv1", "recv2", "recv3", "recv1", "recv1", "recv3"]
        # The test task and the run_ordered_sequence tasks should still be alive
        assert len(asyncio.all_tasks()) == 2
        assert start_run_ordered_sequence in asyncio.all_tasks()
        assert self.selector.is_stopped

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
        """Test that multiple ready receviers are handled properly.

        Also test that the loop waits forever if there are no more receivers ready.
        """
        assert self.selector.is_stopped

        received: set[str] = set()
        last_time: float = self.loop.time()
        async with self.selector:
            try:
                async with asyncio.timeout(15):
                    async for selected in self.selector:
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
                # This happened after time == 3, but the loop never resumes becuase
                # there is nothing ready, so we need to check it after the timeout.
                assert received == {
                    self.recv1.name,
                    self.recv2.name,
                }
                # The selector is still waiting for receivers to be ready.
                assert not self.selector.is_stopped
            else:
                assert False, "Should have timed out"

        assert len(asyncio.all_tasks()) == 1  # The test task should still be alive
        assert self.selector.is_stopped
