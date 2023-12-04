# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the merge implementation."""

import pytest

from frequenz.channels import merge


async def test_empty() -> None:
    """Ensure merge() raises an exception when no receivers are provided."""
    with pytest.raises(ValueError, match="At least one receiver must be provided"):
        merge()
