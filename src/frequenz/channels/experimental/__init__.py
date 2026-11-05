# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Experimental channel primitives.

Warning:
    This package contains experimental channel primitives that are not yet
    considered stable. For more information on what to expect and how to use the
    `experimental` package please read the [`experimental` package
    guidelines](https://github.com/frequenz-floss/docs/blob/v0.x.x/python/experimental-packages.md).
"""

from typing import TYPE_CHECKING, TypeAlias

from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases

from ._grouping_latest_value_cache import (
    DefaultT,
    GroupingLatestValueCache,
    HashableT,
    ValueT_co,
)
from ._optional_receiver import OptionalReceiver
from ._pipe import Pipe
from ._relay_sender import RelaySender

__all__ = [
    "DefaultT",
    "GroupingLatestValueCache",
    "HashableT",
    "NopReceiver",
    "OptionalReceiver",
    "Pipe",
    "RelaySender",
    "ValueT_co",
    "WithPrevious",
]

if TYPE_CHECKING:
    from .._nop_receiver import NopReceiver as _NopReceiver
    from .._with_previous import WithPrevious as _WithPrevious

    NopReceiver: TypeAlias = _NopReceiver
    """A place-holder receiver that will never receive a message.

    Deprecated:
        Deprecated since v1.13.0. Use
        [`frequenz.channels.NopReceiver`][frequenz.channels.NopReceiver] instead.
    """

    WithPrevious: TypeAlias = _WithPrevious
    """A composable predicate to build predicates that can also use the previous message.

    Deprecated:
        Deprecated since v1.13.0. Use
        [`frequenz.channels.WithPrevious`][frequenz.channels.WithPrevious] instead.
    """
else:
    __getattr__ = deprecated_aliases(
        __name__,
        DeprecatedAlias(
            "NopReceiver",
            new_module="frequenz.channels",
            since="v1.13.0",
        ),
        DeprecatedAlias(
            "WithPrevious",
            new_module="frequenz.channels",
            since="v1.13.0",
        ),
    )
