# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for `channel.FileWatcher`."""

from __future__ import annotations

import os
import pathlib
from collections.abc import AsyncGenerator, Iterator, Sequence
from datetime import timedelta
from typing import Any
from unittest import mock

import pytest
from watchfiles import Change
from watchfiles.main import FileChange

from frequenz.channels.util import FileWatcher, Select, Timer


class _FakeAwatch:
    """Fake awatch class to mock the awatch function."""

    def __init__(self, changes: Sequence[FileChange] = ()) -> None:
        """Create a `_FakeAwatch` instance.

        Args:
            changes: A sequence of file changes to be returned by the fake awatch
                function.
        """
        self.changes: Sequence[FileChange] = changes

    async def fake_awatch(
        self, *paths: str, **kwargs: Any  # pylint: disable=unused-argument
    ) -> AsyncGenerator[set[FileChange], None]:
        """Fake awatch function.

        Args:
            paths: Paths to watch.
            kwargs: Keyword arguments to pass to the awatch function.
        """
        for change in self.changes:
            yield {change}


@pytest.fixture
def fake_awatch() -> Iterator[_FakeAwatch]:
    """Fixture to mock the awatch function."""
    fake = _FakeAwatch()
    with mock.patch(
        "frequenz.channels.util._file_watcher.awatch",
        autospec=True,
        side_effect=fake.fake_awatch,
    ):
        yield fake


async def test_file_watcher_receive_updates(
    fake_awatch: _FakeAwatch,  # pylint: disable=redefined-outer-name
) -> None:
    """Test the file watcher receive the expected events."""
    filename = "test-file"
    changes = (
        (Change.added, filename),
        (Change.deleted, filename),
        (Change.modified, filename),
    )
    fake_awatch.changes = changes
    file_watcher = FileWatcher(paths=[filename])

    for change in changes:
        recv_changes = await file_watcher.receive()
        assert recv_changes == pathlib.Path(change[1])


async def test_file_watcher(tmp_path: pathlib.Path) -> None:
    """Ensure file watcher is returning paths on file events.

    Args:
        tmp_path (pathlib.Path): A tmp directory to run the file watcher on.
            Created by pytest.
    """
    filename = tmp_path / "test-file"
    file_watcher = FileWatcher(paths=[str(tmp_path)])

    number_of_writes = 0
    expected_number_of_writes = 3

    select = Select(
        timer=Timer.timeout(timedelta(seconds=0.1)),
        file_watcher=file_watcher,
    )
    while await select.ready():
        if msg := select.timer:
            filename.write_text(f"{msg.inner}")
        elif msg := select.file_watcher:
            assert msg.inner == filename
            number_of_writes += 1
            # After receiving a write 3 times, unsubscribe from the writes channel
            if number_of_writes == expected_number_of_writes:
                break

    assert number_of_writes == expected_number_of_writes


async def test_file_watcher_change_types(tmp_path: pathlib.Path) -> None:
    """Ensure file watcher is returning paths only on the DELETE change.

    Args:
        tmp_path (pathlib.Path): A tmp directory to run the file watcher on.
            Created by pytest.
    """
    filename = tmp_path / "test-file"
    file_watcher = FileWatcher(
        paths=[str(tmp_path)], event_types={FileWatcher.EventType.DELETE}
    )

    select = Select(
        write_timer=Timer.timeout(timedelta(seconds=0.1)),
        deletion_timer=Timer.timeout(timedelta(seconds=0.25)),
        watcher=file_watcher,
    )
    number_of_deletes = 0
    number_of_write = 0
    while await select.ready():
        if msg := select.write_timer:
            filename.write_text(f"{msg.inner}")
            number_of_write += 1
        elif _ := select.deletion_timer:
            os.remove(filename)
        elif _ := select.watcher:
            number_of_deletes += 1
            break

    assert number_of_deletes == 1
    # Can be more because the watcher could take some time to trigger
    assert number_of_write >= 2
