# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the symbols removed from `experimental`."""

import pytest

from frequenz.channels import experimental

_REMOVED = [
    "DefaultT",
    "GroupingLatestValueCache",
    "HashableT",
    "NopReceiver",
    "OptionalReceiver",
    "RelaySender",
    "ValueT_co",
    "WithPrevious",
]


@pytest.mark.parametrize("name", _REMOVED)
def test_removed_symbol_is_gone(name: str) -> None:
    """Ensure the removed symbols are not in `experimental` any more."""
    assert not hasattr(experimental, name)
    assert name not in experimental.__all__


def test_pipe_is_still_there() -> None:
    """Ensure `Pipe` stays in `experimental`."""
    assert experimental.__all__ == ["Pipe"]
