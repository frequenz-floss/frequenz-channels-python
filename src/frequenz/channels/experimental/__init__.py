# License: MIT
# Copyright © 2024 Frequenz Energy-as-a-Service GmbH

"""Experimental channel primitives.

Warning:
    This package contains experimental channel primitives that are not yet
    considered stable. For more information on what to expect and how to use the
    `experimental` package please read the [`experimental` package
    guidelines](https://github.com/frequenz-floss/docs/blob/v0.x.x/python/experimental-packages.md).
"""

from typing import TYPE_CHECKING, TypeAlias, TypeVar

from frequenz.core.warnings import DeprecatedAlias, deprecated_aliases

from ._grouping_latest_value_cache import GroupingLatestValueCache
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

# The type variables of `GroupingLatestValueCache` use a workaround: `@deprecated`
# only works on classes and functions, so it can't mark them. `deprecated_aliases()`
# is meant for symbols that moved or were renamed, but its `__getattr__` is the only
# way to warn when they are reached from here, so their aliases point at the private
# module that defines them, which is not a move. That's also why they need a custom
# `message` and hand-written notices: the generated ones would point at the private
# module. See https://github.com/frequenz-floss/frequenz-core-python/issues/222.
if TYPE_CHECKING:
    from collections.abc import Hashable

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

    # Type variables can't be aliased, so type checkers get new ones, equivalent to
    # the ones in `_grouping_latest_value_cache`.
    DefaultT = TypeVar("DefaultT")
    """Type variable for the default value returned by
    [`GroupingLatestValueCache.get`][frequenz.channels.experimental.GroupingLatestValueCache.get].

    Deprecated:
        Deprecated since v1.13.0, and will be removed in v2.0.0 together with
        [`GroupingLatestValueCache`][frequenz.channels.experimental.GroupingLatestValueCache].
    """

    HashableT = TypeVar("HashableT", bound=Hashable)
    """Type variable for the keys used to group values in the
    [`GroupingLatestValueCache`][frequenz.channels.experimental.GroupingLatestValueCache].

    Deprecated:
        Deprecated since v1.13.0, and will be removed in v2.0.0 together with
        [`GroupingLatestValueCache`][frequenz.channels.experimental.GroupingLatestValueCache].
    """

    ValueT_co = TypeVar("ValueT_co", covariant=True)
    """Covariant type variable for the values cached by the
    [`GroupingLatestValueCache`][frequenz.channels.experimental.GroupingLatestValueCache].

    Deprecated:
        Deprecated since v1.13.0, and will be removed in v2.0.0 together with
        [`GroupingLatestValueCache`][frequenz.channels.experimental.GroupingLatestValueCache].
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
        DeprecatedAlias(
            "DefaultT",
            new_module="frequenz.channels.experimental._grouping_latest_value_cache",
            since="v1.13.0",
            message="{old} is deprecated and will be removed in v2.0.0, together with "
            "frequenz.channels.experimental.GroupingLatestValueCache. Copy it into "
            "your project if you need it.",
        ),
        DeprecatedAlias(
            "HashableT",
            new_module="frequenz.channels.experimental._grouping_latest_value_cache",
            since="v1.13.0",
            message="{old} is deprecated and will be removed in v2.0.0, together with "
            "frequenz.channels.experimental.GroupingLatestValueCache. Copy it into "
            "your project if you need it.",
        ),
        DeprecatedAlias(
            "ValueT_co",
            new_module="frequenz.channels.experimental._grouping_latest_value_cache",
            since="v1.13.0",
            message="{old} is deprecated and will be removed in v2.0.0, together with "
            "frequenz.channels.experimental.GroupingLatestValueCache. Copy it into "
            "your project if you need it.",
        ),
    )
