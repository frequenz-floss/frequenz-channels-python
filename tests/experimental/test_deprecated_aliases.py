# License: MIT
# Copyright © 2026 Frequenz Energy-as-a-Service GmbH

"""Tests for the deprecated aliases of symbols promoted out of `experimental`."""

import pytest
from frequenz.core.warnings import asserting_no_deprecations

import frequenz.channels
from frequenz.channels import experimental

_PROMOTED = ["NopReceiver", "WithPrevious"]


@pytest.mark.parametrize("name", _PROMOTED)
def test_old_name_warns(name: str) -> None:
    """Ensure the old `experimental` name warns and is the very same object."""
    with pytest.deprecated_call(
        match=rf"^frequenz\.channels\.experimental\.{name} is deprecated and will "
        rf"be removed in v2\.0\.0\. Use frequenz\.channels\.{name} instead\.$"
    ):
        old = getattr(experimental, name)
    assert old is getattr(frequenz.channels, name)


@pytest.mark.parametrize("name", _PROMOTED)
def test_new_name_does_not_warn(name: str) -> None:
    """Ensure the new top-level name doesn't warn."""
    with asserting_no_deprecations():
        _ = getattr(frequenz.channels, name)
