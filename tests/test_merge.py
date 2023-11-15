# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the merge implementation."""

from unittest import mock

import pytest

from frequenz.channels import Receiver, merge


async def test_empty() -> None:
    """Ensure merge() raises an exception when no receivers are provided."""
    with pytest.raises(ValueError, match="At least one receiver must be provided"):
        merge()


async def test_one() -> None:
    """Ensure merge() returns the same receiver when only one is provided."""
    receiver = mock.MagicMock(spec=Receiver[int])

    merge_receiver: Receiver[int] = merge(receiver)
    assert merge_receiver is receiver
