# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for `channel.FileWatcher`."""

import os
import pathlib

from frequenz.channels.util import FileWatcher, Select, Timer
from frequenz.channels.util._file_watcher import EventType


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

    select = Select(timer=Timer(0.1), file_watcher=file_watcher)
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
    file_watcher = FileWatcher(paths=[str(tmp_path)], event_types={EventType.DELETE})

    select = Select(
        write_timer=Timer(0.1), deletion_timer=Timer(0.5), watcher=file_watcher
    )
    number_of_receives = 0
    while await select.ready():
        if msg := select.write_timer:
            filename.write_text(f"{msg.inner}")
        elif _ := select.deletion_timer:
            os.remove(filename)
        elif _ := select.watcher:
            number_of_receives += 1
            break
    assert number_of_receives == 1
