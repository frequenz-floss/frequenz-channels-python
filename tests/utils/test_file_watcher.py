# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for `channel.FileWatcher`."""

import os
import pathlib

from frequenz.channels.util import FileWatcher, Select, Timer


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

    timer = Timer(0.1)

    select = Select(timer, file_watcher)
    async for ready_set in select.ready():
        if timer in ready_set:
            msg = timer.consume()
            filename.write_text(f"{msg}")
        if file_watcher in ready_set:
            fname = file_watcher.consume()
            assert fname == filename
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

    write_timer = Timer(0.1)
    deletion_timer = Timer(0.5)
    watcher = file_watcher

    select = Select(write_timer, deletion_timer, watcher)
    number_of_receives = 0
    async for ready_set in select.ready():
        if write_timer in ready_set:
            msg = write_timer.consume()
            filename.write_text(f"{msg}")
        if deletion_timer in ready_set:
            _ = deletion_timer.consume()  # We need to consume the message
            os.remove(filename)
        if watcher in ready_set:
            fname = watcher.consume()
            assert fname == filename
            number_of_receives += 1
            break
    assert number_of_receives == 1
