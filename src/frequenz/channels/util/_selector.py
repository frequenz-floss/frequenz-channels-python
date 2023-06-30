# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Select the first among multiple Receivers.

Expects Receiver class to raise `StopAsyncIteration`
exception once no more messages are expected or the channel
is closed in case of `Receiver` class.
"""

import asyncio
from types import TracebackType
from typing import Any, AsyncIterator, Generic, Self, TypeGuard, TypeVar, assert_never

from .._base_classes import Receiver
from .._exceptions import ReceiverStoppedError

_T = TypeVar("_T")


class Selected(Generic[_T]):
    """A result of a [`Selector`][frequenz.channels.util.Selector] loop iteration.

    The selected receiver is consumed immediately and the received value is stored in
    the instance, unless there was an exception while receiving the value, in which case
    the exception is stored instead.

    `Selected` instances should be used in conjunction with the
    [`selected_from()`][frequenz.channels.util.selected_from] function to determine
    which receiver was selected.

    Please see [`Selector`][frequenz.channels.util.Selector] for an example.
    """

    class _EmptyResult:
        """A sentinel value to distinguish between None and empty result.

        We need a sentinel because a result can also be `None`.
        """

        def __repr__(self) -> str:
            return "<empty>"

    def __init__(self, receiver: Receiver[_T]) -> None:
        """Create a new instance.

        The receiver is consumed immediately when creating the instance and the received
        value is stored in the instance for later use as
        [`value`][frequenz.channels.util.Selected.value].  If there was an exception
        while receiving the value, then the exception is stored in the instance instead
        (as [`exception`][frequenz.channels.util.Selected.exception]).

        Args:
            receiver: The receiver that was selected.
        """
        self._recv: Receiver[_T] = receiver
        """The receiver that was selected."""

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

    def was_stopped(self) -> bool:
        """Check if the selected receiver was stopped.

        Check if the selected receiver raised
        a [`ReceiverStoppedError`][frequenz.channels.ReceiverStoppedError] while
        consuming a value.

        Returns:
            Whether the receiver was stopped.
        """
        return isinstance(self._exception, ReceiverStoppedError)

    def __str__(self) -> str:
        """Return a string representation of this instance.

        Returns:
            A string representation of this instance.
        """
        return (
            f"{type(self).__name__}({self._recv}) -> "
            f"{self._exception or self._value})"
        )

    def __repr__(self) -> str:
        """Return a the internal representation of this instance.

        Returns:
            A string representation of this instance.
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
    """Check if the given receiver was selected by a [`Selector`][frequenz.channels.util.Selector].

    This function is used in conjunction with the
    [`Selected`][frequenz.channels.util.Selected] class to determine which receiver was
    selected in a `Selector` loop iteration.

    It also works as a [type guard][typing.TypeGuard] to narrow the type of the
    `Selected` instance to the type of the receiver.

    Please see [`Selector`][frequenz.channels.util.Selector] for an example.

    Args:
        selected: The result of a `Selector` loop iteration.
        receiver: The receiver to check if it was the source of a select operation.

    Returns:
        Whether the given receiver was selected.
    """
    if handled := selected._recv is receiver:  # pylint: disable=protected-access
        selected._handled = True  # pylint: disable=protected-access
    return handled


class SelectError(BaseException):
    """A base exception for [`Selector`][frequenz.channels.util.Selector].

    This exception is raised when a `Selector` loop iteration fails.  It is raised as
    a single exception when one receiver fails during normal operation (while calling
    `ready()` for example).  It is raised as a group exception
    ([`SelectErrorGroup`][frequenz.channels.util.SelectErrorGroup]) when a `Selector` is
    [`stop()`][frequenz.channels.util.Selector.stop]ed.
    """


class UnhandledSelectedError(SelectError, Generic[_T]):
    """A receiver was not handled in a [`Selector`][frequenz.channels.util.Selector] loop.

    This exception is raised when a `Selector` loop finishes without a call to
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
    """An exception group for [`Selector`][frequenz.channels.util.Selector].

    This exception group is raised when a [`Selector.stop()`] fails while cleaning up
    runing tasts to check for ready receivers.
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


async def select(*receivers: Receiver[Any]) -> AsyncIterator[Selected[Any]]:
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
        import datetime
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
            pending.add(asyncio.create_task(recv.ready(), name=name))

        while pending:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                receiver_active: bool = True
                name = task.get_name()
                recv = receivers_map[name]
                if exception := task.exception():
                    match exception:
                        case asyncio.CancelledError():
                            # If the receiver was cancelled, then it means we want to
                            # exit the select loop, so we handle the receiver but we
                            # don't add it back to the pending list.
                            receiver_active = False
                        case _ as exc:
                            raise SelectError(f"Error while selecting {recv}") from exc

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
                pending.add(asyncio.create_task(recv.ready(), name=name))
    finally:
        await _stop_pending_tasks(pending)


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
            if task.cancelled():
                continue
            if exception := task.exception():
                exceptions.append(exception)
        if exceptions:
            # If the select loop is interrupted by a break or exception, then this
            # exception will be actually swallowed, as the select() async generator
            # will be collected by the asyncio loop. This shouldn't be too bad as
            # errors produced by receivers will be re-raised when trying to use them
            # again.
            raise SelectErrorGroup("Some receivers failed when select()ing", exceptions)


class Selector:
    """A tool to iterate over the values of all receivers as new values become available.

    This tool is used to iterate over the values of all receivers as they receive new
    values.  It is used in conjunction with the
    [`Selected`][frequenz.channels.util.Selected] class and the
    [`selected_from()`][frequenz.channels.util.selected_from] [type
    guard][typing.TypeGuard] to determine which receiver was selected in a `Selector`
    loop iteration.

    An exhaustiveness check is performed at runtime to make sure all selected receivers
    are handled in the loop if-chain.  You must call `selected_from()` with all the
    receivers passed to the `Selector` inside the selection loop, even if you plan to
    ignore a value.  This is to signal the `Selector` that you are purposefully ignoring
    the value and the exhaustiveness check doesn't fail.

    A `Selector` will create one task per receiver to check if it is ready to receive a
    new value.  To make sure tasks are properly destroyed after a selection loop, the
    `Selector` class is an [async context
    manager](https://docs.python.org/3/reference/datamodel.html#async-context-managers).

    When instantiated, a `Selector` [is
    stopped][frequenz.channels.util.Selector.is_stopped], and task are not started until
    [`start()`][frequenz.channels.util.Selector.start] is called or the async context is
    entered.  When the async context is exited, the `Selector` is automatically
    [`stop()`][frequenz.channels.util.Selector.stop]ed.  Because of this, usually you
    should not call `start()` or `stop()` manually.

    Note:
        A `Selector` is intended to be used in cases where the set of receivers is
        static and known beforehand.  If you need to dynamically add/remove receivers
        from a selector, there are a few alternatives.  Depending on your use case,
        one or the other could work better for you:

        * Use [`Merge`][frequenz.channels.util.Merge] or
          [`MergeNamed`][frequenz.channels.util.MergeNamed]: this is useful when you
          have and unknown number of receivers of the same type that can be handled as
          a group.
        * Use tasks to manage each recever individually: this is better if there are no
          relationships between the receivers.
        * Break the `Selector` loop and create new instance with the new set of
          receivers.  This should be the last resort, as it has some performance
          implications because the tasks need to be restarted.

    Example:
        ```python
        import datetime
        from typing import assert_never

        from frequenz.channels import ReceiverStoppedError
        from frequenz.channels.util import Selector, selected_from, Timer

        timer1 = Timer.periodic(datetime.timedelta(seconds=1))
        timer2 = Timer.timeout(datetime.timedelta(seconds=0.5))

        async with Selector(timer1, timer2) as selector:
            async for selected in selector:
                if selected_from(selected, timer1):
                    # Beware: `selected.value` might raise an exception, you can always
                    # check for exceptions with `selected.exception` first or use
                    # a try-except block. You can also quickly check if the receiver was
                    # stopped and let any other unexpected exceptions bubble up.
                    if selected.was_stopped():
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
                                f"timer2: now={datetime.datetime.now()} "
                                f"drift={selected.value}"
                            )
                        case _ as unhanded:
                            assert_never(unhanded)
                else:
                    # This is not necessary, as select() will check for exhaustiveness, but
                    # it is good practice to have it in case you forgot to handle a new
                    # receiver added to `select()` at a later point in time.
                    assert False
        ```
    """

    def __init__(self, *receivers: Receiver[Any]) -> None:
        """Create a new instance.

        Creating a new instance of `Selector` does not start it, so no tasks will be
        created until [`start()`][frequenz.channels.util.Selector.start] is called.
        When a `Selector` is used as a context manager (`async with`) it will
        automatically start, so in general there is no need to worry about calling
        `start()` manually.

        Args:
            *receivers: The receivers to select from.
        """
        self._receivers_map: dict[str, Receiver[Any]] = {
            str(hash(r)): r for r in receivers
        }
        """The map of receiver names to receivers.

        This is used to map tasks names with receivers, so that we can easily find the
        receiver that was selected when a task completes.
        """

        self._pending_tasks: set[asyncio.Task[bool]] = set()
        """The set of pending tasks.

        These tasks are used to wait for the receivers to be ready to receive a new
        value.

        If there are no more pending and done tasks, the selector is considered to be
        done/stopped.
        """

        self._done_tasks: set[asyncio.Task[bool]] = set()
        """The set of done tasks.

        These are tasks that are already done, i.e. the receivers that have a ready
        value to be consumed, but that haven't been selected yet.

        If there are no more pending and done tasks, the selector is considered to be
        done/stopped.
        """

        self._currently_selected: Selected[Any] | None = None
        """The currently selected receiver.

        This is only saved to check for exhaustiveness.
        """

    @property
    def is_stopped(self) -> bool:
        """Whether this selector is currently stopped.

        Returns:
            Whether this selector is currently stopped.
        """
        return not self._pending_tasks and not self._done_tasks

    def start(self) -> None:
        """Start this selector.

        This will create a task for each receiver passed to the constructor, and
        schedule them to run.  If this selector is already running, this method does
        nothing.
        """
        if not self.is_stopped:
            return
        for name, recv in self._receivers_map.items():
            self._pending_tasks.add(asyncio.create_task(recv.ready(), name=name))

    def cancel(self) -> None:
        """Cancel this selector.

        This will cancel all pending tasks, but won't wait for them to complete.  If
        you want to wait for them to complete, you can use
        [`stop()`][frequenz.channels.util.Selector.stop] instead.

        This can be used to asynchronously stop this selector.
        """
        for task in self._pending_tasks:
            task.cancel()

    async def stop(self) -> None:
        """Stop this selector.

        This will cancel all pending tasks, and wait for them to complete.  If you
        don't want to wait for them to complete, you can use
        [`cancel()`][frequenz.channels.util.Selector.cancel] instead.

        Raises:
            SelectErrorGroup: If there is an error in any of the pending receivers.
        """
        self.cancel()
        if exceptions := await self._wait_for_pending_tasks():
            raise SelectErrorGroup("Some receivers failed when select()ing", exceptions)

    async def __aenter__(self) -> Self:
        """Start this selector if it is not already running.

        Returns:
            This selector.

        """
        self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Stop this selector.

        Args:
            exc_type: The type of the exception raised, if any.
            exc_val: The exception raised, if any.
            exc_tb: The traceback of the exception raised, if any.
        """
        await self.stop()

    def __del__(self) -> None:
        """Delete this `Selector`.

        Cancel all the pending tasks.
        """
        self.cancel()

    def __aiter__(self) -> Self:
        """Return self as an async iterator over the selected values.

        Returns:
            This selector.
        """
        return self

    async def __anext__(self) -> Selected[Any]:
        """Iterate over the values of all receivers as they receive new values.

        Returns:
            The currently selected item.

        Raises:
            UnhandledSelectedError: If the previously selected receiver was not handled
                (`select_from` was not called with the selected receiver) in the
                if-chain.
            SelectError: If there is an internal error in this selector or a receiver
                raises an exception while waiting to be ready.  Errors while consuming
                from the receiver are not raised, but reported via the `Selected`
                instance.
            StopAsyncIteration: If the `Selector` was not
                [`start()`][frequenz.channels.util.Selector.start]ed, all the receivers
                were stopped, or [`cancel()`][frequenz.channels.util.Selector.cancel]
                was called.
        """
        # Check for exhaustiveness
        selected = self._currently_selected
        self._currently_selected = None
        if selected and not selected._handled:  # pylint: disable=protected-access
            raise UnhandledSelectedError(selected)

        # If we already have some receivers that are done, we can select from them
        # without waiting again, but tasks could be done because they were cancelled,
        # so we need to check if there is actually a selected receiver.
        if self._done_tasks:
            if selected := self._select_next():
                return selected

        # If there are no more receivers that are done and no pending receivers either,
        # we are done.
        # From now on, we need to wait for some pending receivers to be ready.
        while self._pending_tasks:
            # If there are pending receivers, we wait for some to be ready.
            self._done_tasks, self._pending_tasks = await asyncio.wait(
                self._pending_tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            # At this point, **something** should be done, but tasks could be done
            # because they were cancelled, so we need to check if there is actually
            # a selected receiver.
            assert self._done_tasks
            if selected := self._select_next():
                return selected

        # If we reached this point, there are no more pending tasks and all done tasks
        # were cancelled, so we are done with the loop
        assert not self._done_tasks
        raise StopAsyncIteration()

    def _select_next(self) -> Selected[Any] | None:
        """Select the next receiver that is ready.

        This will select the next receiver that is ready from the list of done tasks,
        and return it as a `Selected` instance.

        If there is no receiver that is ready (for example because all done tasks are
        from receivers that were stopped or because the tasks were cancelled), this
        will return `None`.

        Returns:
            The selected receiver, or `None` if there is no selected receiver.

        Raises:
            SelectError: If there is an internal error in this selector or a receiver
                raises an exception while waiting to be ready.
        """
        while self._done_tasks:
            done_task = self._done_tasks.pop()
            name = done_task.get_name()
            recv = self._receivers_map[name]
            # If the task was cancelled, we just skip it and don't add if back to the
            # pending list because we are being cancelled.
            if done_task.cancelled():
                print(f"Cancelled {recv}")
                continue
            # If there is any other exception (unexpected, as ready() should not
            # raise), we re-raise it as a SelectError.
            if exception := done_task.exception():
                raise SelectError(f"Error while selecting {recv}") from exception

            self._currently_selected = Selected(recv)

            receiver_active = done_task.result()  # False
            receiver_stopped = self._currently_selected.was_stopped()  # True
            if receiver_active and not receiver_stopped:
                # Add back the receiver to the pending list if it is still active.
                name = done_task.get_name()
                recv = self._receivers_map[name]
                self._pending_tasks.add(asyncio.create_task(recv.ready(), name=name))

            return self._currently_selected
        return None

    async def _wait_for_pending_tasks(self) -> list[BaseException]:
        """Wait for all pending tasks to be done.

        If the pending tasks were cancelled or the underlying receiver was stopped, then
        these exceptions will be ignored.  Other exceptions will be returned.

        All pending and done tasks will be cleared.

        Returns:
            The list of exceptions raised by the pending tasks.
        """
        if not self._pending_tasks:
            return []

        self._done_tasks, self._pending_tasks = await asyncio.wait(self._pending_tasks)
        assert not self._pending_tasks
        exceptions: list[BaseException] = []
        while self._done_tasks:
            task = self._done_tasks.pop()
            if task.cancelled():
                continue
            # The assignment is a workaround for a mypy bug not doing
            # proper exhaustiveness checking otherwise:
            # https://github.com/python/mypy/issues/12998
            exception = task.exception()
            match exception:
                # We ignore ReceiverStoppedError too because they will be re-raised if
                # the user tries to receive from the receiver again, so there is no
                # information loss, and knowing that a receiver stopped when stopping
                # the select loop doesn't provide a lot of info and it might even be
                # confusing as we swallow ReceiverStoppedError during normal operation
                # too.
                case None | ReceiverStoppedError():
                    pass
                case BaseException():
                    exceptions.append(exception)
                case _ as unhandled:
                    assert_never(unhandled)
        return exceptions
