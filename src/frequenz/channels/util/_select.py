# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Select the first among multiple Receivers.

Expects Receiver class to raise `StopAsyncIteration`
exception once no more messages are expected or the channel
is closed in case of `Receiver` class.
"""

import asyncio
import datetime
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Generic, TypeGuard, TypeVar

from .._base_classes import Receiver
from .._exceptions import ReceiverStoppedError

logger = logging.Logger(__name__)
_T = TypeVar("_T")


class Selected(Generic[_T]):
    """The result of a [`select()`][frequenz.channels.util.select] operation.

    This class is used as the result of a select operation.  The selected receiver is
    consumed immediately and the received value is stored in the instance, unless there
    was an exception while receiving the value, in which case the exception is stored
    instead.

    `Selected` instances should be used in conjunction with the
    [`selected_from()`][frequenz.channels.util.selected_from] function to determine
    which receiver was selected.

    Please see [`select()`][frequenz.channels.util.select] for an example.
    """

    class _EmptyResult:
        def __repr__(self) -> str:
            return "<empty>"

    def __init__(self, receiver: Receiver[_T]) -> None:
        """Create a new instance.

        The receiver is consumed immediately when creating the instance and the received
        value is stored in the instance for later use as `value`. If there was an
        exception while receiving the value, then the exception is stored in the
        instance instead (as `exception`).

        Args:
            receiver: The receiver that was selected.
        """
        self._recv: Receiver[_T] = receiver
        """The receiver that was selected."""

        # We need a sentinel value to distinguish between None and empty result
        # because a result can be None
        self._value: _T | Selected._EmptyResult = Selected._EmptyResult()
        """The value that was received.

        If there was an exception while receiving the value, then this will be `None`.
        """
        self._exception: Exception | None = None
        """The exception that was raised while receiving the value (if any)."""

        try:
            self._value = receiver.consume()
        except Exception as exc:  # pylint: disable=broad-except
            self._exception = exc

        self._handled: bool = False
        """Flag to indicate if this selected has been handled in the if-chain."""

    @property
    def value(self) -> _T:
        """The value that was received, if any.

        Returns:
            The value that was received.

        Raises:
            Exception: If there was an exception while receiving the value. Normally
                this should be an [`frequenz.channels.Error`][frequenz.channels.Error]
                instance, but catches all exceptions in case some receivers can raise
                anything else.

        # noqa: DAR401 _exception
        """
        if self._exception is not None:
            raise self._exception
        assert not isinstance(self._value, Selected._EmptyResult)
        return self._value

    @property
    def exception(self) -> Exception | None:
        """The exception that was raised while receiving the value (if any).

        Returns:
            The exception that was raised while receiving the value (if any).
        """
        return self._exception

    @property
    def was_stopped(self) -> bool:
        """Whether the receiver was stopped.

        A receiver is considered stopped if it raised a `ReceiverStoppedError` while
        receiving a value.

        Returns:
            Whether the receiver was stopped.
        """
        return isinstance(self._exception, ReceiverStoppedError)

    def __str__(self) -> str:
        """Return a string representation of the instance.

        Returns:
            A string representation of the instance.
        """
        return (
            f"{type(self).__name__}({self._recv}) -> "
            f"{self._exception or self._value})"
        )

    def __repr__(self) -> str:
        """Return a the internal representation of the instance.

        Returns:
            A string representation of the instance.
        """
        return (
            f"{type(self).__name__}({self._recv=}, {self._value=}, "
            f"{self._exception=}, {self._handled=})"
        )


# It would have been nice to be able to make this a method of selected, but sadly
# `TypeGuard`s can't be used as methods. For more information see:
# https://github.com/microsoft/pyright/discussions/3125
def selected_from(
    selected: Selected[Any], receiver: Receiver[_T]
) -> TypeGuard[Selected[_T]]:
    """Check if the given receiver was [`select()`][frequenz.channels.util.select]ed.

    This function is used in conjunction with the `Selected` class to determine which
    receiver was selected in a select operation.

    It also works as a type guard to narrow the type of the `Selected` instance to the
    type of the receiver.

    Please see [`select()`][frequenz.channels.util.select] for an example.

    Args:
        selected: The result of a select operation.
        receiver: The receiver to check.

    Returns:
        Whether the given receiver was selected.
    """
    if handled := selected._recv is receiver:  # pylint: disable=protected-access
        selected._handled = True  # pylint: disable=protected-access
    return handled


class SelectError(BaseException):
    """A base exception for [`select()`][frequenz.channels.util.select] operations.

    This exception is raised when a select operation fails.  It is raised as a single
    exception when one receiver fails during normal operation (while calling `ready()`
    for example).  It is raised as a group exception
    ([`SelectErrorGroup`][frequenz.channels.util.SelectErrorGroup]) when multiple
    receivers fail at the same time (while cleaning up for example).
    """


class UnhandledSelectedError(SelectError, Generic[_T]):
    """A receiver was not handled in [`select()`][frequenz.channels.util.select].

    This exception is raised when a select loop finishes without a call to
    [`selected_from()`][frequenz.channels.util.selected_from] for the selected receiver.
    """

    def __init__(self, selected: Selected[_T]) -> None:
        """Create a new instance.

        Args:
            selected: The selected receiver that was not handled.
        """
        recv = selected._recv  # pylint: disable=protected-access
        super().__init__(f"Selected receiver {recv} was not handled in the if-chain")
        self.selected = selected


class SelectErrorGroup(BaseExceptionGroup[BaseException], SelectError):
    """An exception group for [`select()`][frequenz.channels.util.select] operations.

    This exception group is raised when a select operation fails while cleaning up, so
    many receivers could fail at the same time.
    """


# Typing for select() is tricky.  We had the idea of using a declarative design for
# select, something like:
#
# ```python
# class MySelector(Selector):
#     receiver1: x.new_receiver()
#     receiver2: y.new_receiver()
#
# async for selected in MySelector:
#     if selected.receiver is receiver1:
#         # Do something with selected.value
#     elif selected.receiver is receiver1:
#         # Do something with selected.value
# ```
#
# This is similar to `Enum`, but `Enum` has special support in `mypy` that we can't
# have.
#
# With the current implementation, the typing could be slightly improved by using
# `TypeVarTuple`, but we are not because "transformations" are not supported yet, see:
# https://github.com/python/typing/issues/1216
#
# Also support for `TypeVarTuple` in general is still experimental (and very incomplete
# in `mypy`).
#
# With this we would also probably be able to properly type `select` and *maybe* even be
# able to leverage the exhaustiveness checking of `mypy` to make sure the selected value
# is narrowed down to the correct type to make sure all receivers are handled, with the
# help of `assert_never` as described in:
# https://docs.python.org/3.11/library/typing.html#typing.assert_never
#
# We also explored the possibility of using `match` to perform exhaustiveness checking,
# but we couldn't find a way to make it work with `match`, and `match` is not yet
# checked for exhaustiveness by `mypy` anyway, see:
# https://github.com/python/mypy/issues/13597
async def select(
    *receivers: Receiver[Any], timeout: datetime.timedelta | None = None
) -> AsyncIterator[Selected[Any]]:
    """Iterate over the values of all receivers as they receive new values.

    This function is used to iterate over the values of all receivers as they receive
    new values.  It is used in conjunction with the
    [`Selected`][frequenz.channels.util.Selected] class and the
    [`selected_from()`][frequenz.channels.util.selected_from] function to determine
    which function to determine which receiver was selected in a select operation.

    An exhaustiveness check is performed at runtime to make sure all selected receivers
    are handled in the if-chain, so you should call `selected_from()` with all the
    receivers passed to `select()` inside the select loop, even if you plan to ignore
    a value, to signal `select()` that you are purposefully ignoring the value.

    Note:
        The `select()` function is intended to be used in cases where the set of
        receivers is static and known beforehand.  If you need to dynamically add/remove
        receivers from a select loop, there are a few alternatives.  Depending on your
        use case, one or the other could work better for you:

        * Use [`Merge`][frequenz.channels.util.Merge] or
          [`MergeNamed`][frequenz.channels.util.MergeNamed]: this is useful when you
          have and unknown number of receivers of the same type that can be handled as
          a group.
        * Use tasks to manage each recever individually: this is better if there are no
          relationships between the receivers.
        * Break the `select()` loop and start a new one with the new set of receivers
          (this should be the last resort, as it has some performance implications
           because the loop needs to be restarted).

    Example:
        ```python
        from typing import assert_never

        from frequenz.channels import ReceiverStoppedError
        from frequenz.channels.util import select, selected_from, Timer

        timer1 = Timer.periodic(datetime.timedelta(seconds=1))
        timer2 = Timer.timeout(datetime.timedelta(seconds=0.5))

        async for selected in select(timer1, timer2):
            if selected_from(selected, timer1):
                # Beware: `selected.value` might raise an exception, you can always
                # check for exceptions with `selected.exception` first or use
                # a try-except block. You can also quickly check if the receiver was
                # stopped and let any other unexpected exceptions bubble up.
                if selected.was_stopped:
                    print("timer1 was stopped")
                    continue
                print(f"timer1: now={datetime.datetime.now()} drift={selected.value}")
                timer2.stop()
            elif selected_from(selected, timer2):
                # Explicitly handling of exceptions
                match selected.exception:
                    case ReceiverStoppedError():
                        print("timer2 was stopped")
                    case Exception() as exception:
                        print(f"timer2: exception={exception}")
                    case None:
                        # All good, no exception, we can use `selected.value` safely
                        print(
                            f"timer2: now={datetime.datetime.now()} drift={selected.value}"
                        )
                    case _ as unhanded:
                        assert_never(unhanded)
            else:
                # This is not necessary, as select() will check for exhaustiveness, but
                # it is good practice to have it in case you forgot to handle a new
                # receiver added to `select()` at a later point in time.
                assert False
        ```

    Args:
        *receivers: The receivers to select from.
        timeout: The timeout for the select operation.  If not `None`, the loop will
            block for at most the specified time.  If the timeout is reached, the
            iteration will stop.

    Yields:
        The currently selected item.

    Raises:
        UnhandledSelectedError: If a selected receiver was not handled in the if-chain.
        SelectErrorGroup: If there is an error while finishing the select operation and
            receivers fail while cleaning up.
        SelectError: If there is an error while selecting receivers during normal
            operation.  For example if a receiver raises an exception in the `ready()`
            method.  Normal errors while receiving values are not raised, but reported
            via the `Selected` instance.
    """
    receivers_map: dict[str, Receiver[Any]] = {str(hash(r)): r for r in receivers}
    pending: set[asyncio.Task[bool]] = set()

    try:
        for name, recv in receivers_map.items():
            pending.add(asyncio.create_task(_recv_task(recv), name=name))

        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED,
                timeout=timeout.total_seconds() if timeout else None,
            )

            # If the timeout is reached, then we return immediately
            if not done and timeout:
                return

            for task in done:
                name = task.get_name()
                recv = receivers_map[name]
                if exception := task.exception():
                    raise SelectError(f"Error while selecting {recv}") from exception

                selected = Selected(recv)
                yield selected
                if not selected._handled:  # pylint: disable=protected-access
                    raise UnhandledSelectedError(selected)

                receiver_active = task.result()
                if not receiver_active:
                    continue

                # Add back the receiver to the pending list
                name = task.get_name()
                recv = receivers_map[name]
                pending.add(asyncio.create_task(_recv_task(recv), name=name))
    finally:
        await _stop_pending_tasks(pending)


async def _recv_task(recv: Receiver[Any]) -> bool:
    """Wait for a receiver to be ready catching `CancelledError` exceptions.

    It catches `CancelledError` exceptions and returns `False` to indicate that the
    receiver is no longer active.

    Args:
        recv: The receiver to check.

    Returns:
        Whether the receiver is still active.
    """
    try:
        return await recv.ready()
    except asyncio.CancelledError:
        return False


async def _stop_pending_tasks(pending: set[asyncio.Task[bool]]) -> None:
    """Stop all pending tasks.

    Args:
        pending: The pending tasks to stop.

    Raises:
        SelectErrorGroup: If the receivers raise any exceptions.
    """
    if pending:
        for task in pending:
            task.cancel()
        done, pending = await asyncio.wait(pending)
        assert not pending
        exceptions: list[BaseException] = []
        for task in done:
            if exception := task.exception():
                if not isinstance(exception, asyncio.CancelledError):
                    exceptions.append(exception)
        if exceptions:
            raise SelectErrorGroup("Some receivers failed when select()ing", exceptions)


@dataclass
class _Selected:
    """A wrapper class for holding values in `Select`.

    Using this wrapper class allows `Select` to inform user code when a
    receiver gets closed.
    """

    inner: Any


@dataclass
class _ReadyReceiver:
    """A class for tracking receivers that have a message ready to be read.

    Used to make sure that receivers are not consumed from until messages are accessed
    by user code, at which point, it will be converted into a `_Selected` object.

    When a channel has closed,  `recv` should be `None`.
    """

    recv: Receiver[Any] | None

    def get(self) -> _Selected:
        """Consume a message from the receiver and return a `_Selected` object.

        Returns:
            An instance of `_Selected` holding a value from the receiver.
        """
        if self.recv is None:
            return _Selected(None)
        return _Selected(self.recv.consume())  # pylint: disable=protected-access


class Select:
    """Select the next available message from a group of Receivers.

    If `Select` was created with more `Receiver` than what are read in
    the if-chain after each call to
    [ready()][frequenz.channels.util.Select.ready], messages coming in the
    additional receivers are dropped, and a warning message is logged.

    [Receiver][frequenz.channels.Receiver]s also function as `Receiver`.

    When Select is no longer needed, then it should be stopped using
    `self.stop()` method. This would cleanup any internal pending async tasks.

    Example:
        For example, if there are two receivers that you want to
        simultaneously wait on, this can be done with:

        ```python
        from frequenz.channels import Broadcast

        channel1 = Broadcast[int]("input-chan-1")
        channel2 = Broadcast[int]("input-chan-2")
        receiver1 = channel1.new_receiver()
        receiver2 = channel2.new_receiver()

        select = Select(name1 = receiver1, name2 = receiver2)
        while await select.ready():
            if msg := select.name1:
                if val := msg.inner:
                    # do something with `val`
                    pass
                else:
                    # handle closure of receiver.
                    pass
            elif msg := select.name2:
                # do something with `msg.inner`
                pass
        ```
    """

    def __init__(self, **kwargs: Receiver[Any]) -> None:
        """Create a `Select` instance.

        Args:
            **kwargs: sequence of receivers
        """
        self._receivers = kwargs
        self._pending: set[asyncio.Task[bool]] = set()

        for name, recv in self._receivers.items():
            self._pending.add(asyncio.create_task(recv.ready(), name=name))

        self._ready_count = 0
        self._prev_ready_count = 0
        self._result: dict[str, _ReadyReceiver | None] = {
            name: None for name in self._receivers
        }

    def __del__(self) -> None:
        """Cleanup any pending tasks."""
        for task in self._pending:
            if not task.done() and task.get_loop().is_running():
                task.cancel()

    async def stop(self) -> None:
        """Stop the `Select` instance and cleanup any pending tasks."""
        for task in self._pending:
            task.cancel()
        await asyncio.gather(*self._pending, return_exceptions=True)
        self._pending = set()

    async def ready(self) -> bool:
        """Wait until there is a message in any of the receivers.

        Returns `True` if there is a message available, and `False` if all
        receivers have closed.

        Returns:
            Whether there are further messages or not.
        """
        # This function will change radically soon
        # pylint: disable=too-many-nested-blocks
        if self._ready_count > 0:
            if self._ready_count == self._prev_ready_count:
                dropped_names: list[str] = []
                for name, value in self._result.items():
                    if value is not None:
                        dropped_names.append(name)
                        if value.recv is not None:
                            try:
                                value.recv.consume()
                            except ReceiverStoppedError:
                                pass
                        self._result[name] = None
                self._ready_count = 0
                self._prev_ready_count = 0
                logger.warning(
                    "Select.ready() dropped data from receiver(s): %s, "
                    "because no messages have been fetched since the last call to ready().",
                    dropped_names,
                )
            else:
                self._prev_ready_count = self._ready_count
                return True
        if len(self._pending) == 0:
            return False

        # once all the pending messages have been consumed, reset the
        # `_prev_ready_count` as well, and wait for new messages.
        self._prev_ready_count = 0

        done, self._pending = await asyncio.wait(
            self._pending, return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            name = task.get_name()
            recv = self._receivers[name]
            receiver_active = task.result()
            if receiver_active:
                ready_recv = recv
            else:
                ready_recv = None
            self._ready_count += 1
            self._result[name] = _ReadyReceiver(ready_recv)
            # if channel or Receiver is closed
            # don't add a task for it again.
            if not receiver_active:
                continue
            self._pending.add(asyncio.create_task(recv.ready(), name=name))
        return True

    def __getattr__(self, name: str) -> Any:
        """Return the latest unread message from a `Receiver`, if available.

        Args:
            name: Name of the channel.

        Returns:
            Latest unread message for the specified `Receiver`, or `None`.

        Raises:
            KeyError: when the name was not specified when creating the
                `Select` instance.
        """
        result = self._result[name]
        if result is None:
            return result
        self._result[name] = None
        self._ready_count -= 1
        return result.get()
