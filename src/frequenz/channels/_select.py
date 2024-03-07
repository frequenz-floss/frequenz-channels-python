# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Select the first among multiple Receivers.

# Usage

If you need to receiver different types of messages from different receivers, you need
to know the source of a particular received message to know the type of the message.

[`select()`][frequenz.channels.select] allows you to do that. It is an
[async iterator][typing.AsyncIterator] that will iterate over the messages of all
receivers as they receive new messages.

It yields a [`Selected`][frequenz.channels.Selected] object that will tell you the
source of the received message. To make sure the received message is *cast* to the
correct type, you need to use the [`selected_from()`][frequenz.channels.selected_from]
function to check the source of the message, and the
[`message`][frequenz.channels.Selected.message] attribute to access the message:

```python show_lines="8:"
from frequenz.channels import Anycast, ReceiverStoppedError, select, selected_from

channel1: Anycast[int] = Anycast(name="channel1")
channel2: Anycast[str] = Anycast(name="channel2")
receiver1 = channel1.new_receiver()
receiver2 = channel2.new_receiver()

async for selected in select(receiver1, receiver2):
    if selected_from(selected, receiver1):
        print(f"Received from receiver1, next number: {selected.message + 1}")
    elif selected_from(selected, receiver2):
        print(f"Received from receiver2, length: {len(selected.message)}")
    else:
        assert False, "Unknown source, this should never happen"
```

Tip:
    To prevent common bugs, like when a new receiver is added to the select loop but
    the handling code is forgotten, [`select()`][frequenz.channels.select] will check
    that all the selected receivers are handled in the if-chain.

    If this happens, it will raise an
    [`UnhandledSelectedError`][frequenz.channels.UnhandledSelectedError] exception.

    If for some reason you want to ignore a received message, just add the receiver to
    the if-chain and do nothing with the message:

    ```python show_lines="8:"
    from frequenz.channels import Anycast, select, selected_from

    channel1: Anycast[int] = Anycast(name="channel1")
    channel2: Anycast[str] = Anycast(name="channel2")
    receiver1 = channel1.new_receiver()
    receiver2 = channel2.new_receiver()

    async for selected in select(receiver1, receiver2):
        if selected_from(selected, receiver1):
            continue
        if selected_from(selected, receiver2):
            print(f"Received from receiver2, length: {len(selected.message)}")
    ```

# Stopping

The `select()` async iterator will stop as soon as all the receivers are stopped. You
can also end the iteration early by breaking out of the loop as normal.

When a single [receiver][frequenz.channels.Receiver] is stopped, it will be reported
via the [`Selected`][frequenz.channels.Selected] object. You can use the
[`was_stopped`][frequenz.channels.Selected.was_stopped] method to check if the
selected [receiver][frequenz.channels.Receiver] was stopped:

```python show_lines="8:"
from frequenz.channels import Anycast, select, selected_from

channel1: Anycast[int] = Anycast(name="channel1")
channel2: Anycast[str] = Anycast(name="channel2")
receiver1 = channel1.new_receiver()
receiver2 = channel2.new_receiver()

async for selected in select(receiver1, receiver2):
    if selected_from(selected, receiver1):
        if selected.was_stopped:
            print("receiver1 was stopped")
            continue
        print(f"Received from receiver1, the next number is: {selected.message + 1}")
    # ...
```

Tip:
    The [`was_stopped`][frequenz.channels.Selected.was_stopped] method is a
    convenience method that is equivalent to checking if the
    [`exception`][frequenz.channels.Selected.exception] attribute is an instance of
    [`ReceiverStoppedError`][frequenz.channels.ReceiverStoppedError].

# Error Handling

Tip:
    For more information about handling errors, please refer to the
    [Error Handling](/user-guide/error-handling/) section of the user guide.

If a receiver raises an exception while receiving a message, the exception will be
raised by the [`message`][frequenz.channels.Selected.message] attribute of the
[`Selected`][frequenz.channels.Selected] object.

You can use a try-except block to handle exceptions as usual:

```python show_lines="8:"
from frequenz.channels import Anycast, ReceiverStoppedError, select, selected_from

channel1: Anycast[int] = Anycast(name="channel1")
channel2: Anycast[str] = Anycast(name="channel2")
receiver1 = channel1.new_receiver()
receiver2 = channel2.new_receiver()

async for selected in select(receiver1, receiver2):
    if selected_from(selected, receiver1):
        try:
            print(f"Received from receiver1, next number: {selected.message + 1}")
        except ReceiverStoppedError:
            print("receiver1 was stopped")
        except ValueError as value_error:
            print(f"receiver1 raised a ValueError: {value_error}")
        # ...
    # ...
```

The [`Selected`][frequenz.channels.Selected] object also has a
[`exception`][frequenz.channels.Selected.exception] attribute that will contain the
exception that was raised by the receiver.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Generic, TypeGuard

from ._exceptions import Error
from ._generic import ReceiverMessageT_co
from ._receiver import Receiver, ReceiverStoppedError


class _EmptyResult:
    """A sentinel value to distinguish between None and empty result.

    We need a sentinel because a result can also be `None`.
    """

    def __repr__(self) -> str:
        """Return a string with the internal representation of this instance."""
        return "<empty>"


class Selected(Generic[ReceiverMessageT_co]):
    """A result of a [`select()`][frequenz.channels.select] iteration.

    The selected receiver is consumed immediately and the received message is stored in
    the instance, unless there was an exception while receiving the message, in which
    case the exception is stored instead.

    `Selected` instances should be used in conjunction with the
    [`selected_from()`][frequenz.channels.selected_from] function to determine
    which receiver was selected.

    Please see [`select()`][frequenz.channels.select] for an example.
    """

    def __init__(self, receiver: Receiver[ReceiverMessageT_co], /) -> None:
        """Initialize this selected result.

        The receiver is consumed immediately when creating the instance and the received
        message is stored in the instance for later use as
        [`message`][frequenz.channels.Selected.message].  If there was an exception
        while receiving the message, then the exception is stored in the instance
        instead (as [`exception`][frequenz.channels.Selected.exception]).

        Args:
            receiver: The receiver that was selected.
        """
        self._recv: Receiver[ReceiverMessageT_co] = receiver
        """The receiver that was selected."""

        self._message: ReceiverMessageT_co | _EmptyResult = _EmptyResult()
        """The message that was received.

        If there was an exception while receiving the message, then this will be `None`.
        """
        self._exception: Exception | None = None
        """The exception that was raised while receiving the message (if any)."""

        try:
            self._message = receiver.consume()
        except Exception as exc:  # pylint: disable=broad-except
            self._exception = exc

        self._handled: bool = False
        """Flag to indicate if this selected has been handled in the if-chain."""

    @property
    def message(self) -> ReceiverMessageT_co:
        """The message that was received, if any.

        Returns:
            The message that was received.

        Raises:
            Exception: If there was an exception while receiving the message. Normally
                this should be an [`frequenz.channels.Error`][frequenz.channels.Error]
                instance, but catches all exceptions in case some receivers can raise
                anything else.
        """
        if self._exception is not None:
            raise self._exception
        assert not isinstance(self._message, _EmptyResult)
        return self._message

    @property
    def exception(self) -> Exception | None:
        """The exception that was raised while receiving the message (if any).

        Returns:
            The exception that was raised while receiving the message (if any).
        """
        return self._exception

    @property
    def was_stopped(self) -> bool:
        """Whether the selected receiver was stopped while receiving a message."""
        return isinstance(self._exception, ReceiverStoppedError)

    def __str__(self) -> str:
        """Return a string representation of this selected receiver."""
        return (
            f"{type(self).__name__}({self._recv}) -> "
            f"{self._exception or self._message})"
        )

    def __repr__(self) -> str:
        """Return a string with the internal representation of this instance."""
        return (
            f"{type(self).__name__}({self._recv=}, {self._message=}, "
            f"{self._exception=}, {self._handled=})"
        )


# It would have been nice to be able to make this a method of selected, but sadly
# `TypeGuard`s can't be used as methods. For more information see:
# https://github.com/microsoft/pyright/discussions/3125
def selected_from(
    selected: Selected[Any], receiver: Receiver[ReceiverMessageT_co]
) -> TypeGuard[Selected[ReceiverMessageT_co]]:
    """Check whether the given receiver was selected by [`select()`][frequenz.channels.select].

    This function is used in conjunction with the
    [`Selected`][frequenz.channels.Selected] class to determine which receiver was
    selected in `select()` iteration.

    It also works as a [type guard][typing.TypeGuard] to narrow the type of the
    `Selected` instance to the type of the receiver.

    Please see [`select()`][frequenz.channels.select] for an example.

    Args:
        selected: The result of a `select()` iteration.
        receiver: The receiver to check if it was the source of a select operation.

    Returns:
        Whether the given receiver was selected.
    """
    if handled := selected._recv is receiver:  # pylint: disable=protected-access
        selected._handled = True  # pylint: disable=protected-access
    return handled


class SelectError(Error):
    """An error that happened during a [`select()`][frequenz.channels.select] operation.

    This exception is raised when a `select()` iteration fails.  It is raised as
    a single exception when one receiver fails during normal operation (while calling
    `ready()` for example).  It is raised as a group exception
    ([`BaseExceptionGroup`][]) when a `select` loop is cleaning up after it's done.
    """


class UnhandledSelectedError(SelectError, Generic[ReceiverMessageT_co]):
    """A receiver was not handled in a [`select()`][frequenz.channels.select] iteration.

    This exception is raised when a [`select()`][frequenz.channels.select] iteration
    finishes without a call to [`selected_from()`][frequenz.channels.selected_from] for
    the selected receiver.
    """

    def __init__(self, selected: Selected[ReceiverMessageT_co]) -> None:
        """Initialize this error.

        Args:
            selected: The selected receiver that was not handled.
        """
        recv = selected._recv  # pylint: disable=protected-access
        super().__init__(f"Selected receiver {recv} was not handled in the if-chain")
        self.selected: Selected[ReceiverMessageT_co] = selected
        """The selected receiver that was not handled."""


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
#         # Do something with selected.message
#     elif selected.receiver is receiver1:
#         # Do something with selected.message
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
# able to leverage the exhaustiveness checking of `mypy` to make sure the selected
# message is narrowed down to the correct type to make sure all receivers are handled,
# with the help of `assert_never` as described in:
# https://docs.python.org/3.11/library/typing.html#typing.assert_never
#
# We also explored the possibility of using `match` to perform exhaustiveness checking,
# but we couldn't find a way to make it work with `match`, and `match` is not yet
# checked for exhaustiveness by `mypy` anyway, see:
# https://github.com/python/mypy/issues/13597


async def select(*receivers: Receiver[Any]) -> AsyncIterator[Selected[Any]]:
    """Iterate over the messages of all receivers as they receive new messages.

    This function is used to iterate over the messages of all receivers as they receive
    new messages.  It is used in conjunction with the
    [`Selected`][frequenz.channels.Selected] class and the
    [`selected_from()`][frequenz.channels.selected_from] function to determine
    which function to determine which receiver was selected in a select operation.

    An exhaustiveness check is performed at runtime to make sure all selected receivers
    are handled in the if-chain, so you should call `selected_from()` with all the
    receivers passed to `select()` inside the select loop, even if you plan to ignore
    a message, to signal `select()` that you are purposefully ignoring the message.

    Note:
        The `select()` function is intended to be used in cases where the set of
        receivers is static and known beforehand.  If you need to dynamically add/remove
        receivers from a select loop, there are a few alternatives.  Depending on your
        use case, one or the other could work better for you:

        * Use [`merge()`][frequenz.channels.merge]: this is useful when you have an
          unknown number of receivers of the same type that can be handled as a group.
        * Use tasks to manage each receiver individually: this is better if there are no
          relationships between the receivers.
        * Break the `select()` loop and start a new one with the new set of receivers
          (this should be the last resort, as it has some performance implications
           because the loop needs to be restarted).

    Example:
        ```python
        import datetime
        from typing import assert_never

        from frequenz.channels import ReceiverStoppedError, select, selected_from
        from frequenz.channels.timer import SkipMissedAndDrift, Timer, TriggerAllMissed

        timer1 = Timer(datetime.timedelta(seconds=1), TriggerAllMissed())
        timer2 = Timer(datetime.timedelta(seconds=0.5), SkipMissedAndDrift())

        async for selected in select(timer1, timer2):
            if selected_from(selected, timer1):
                # Beware: `selected.message` might raise an exception, you can always
                # check for exceptions with `selected.exception` first or use
                # a try-except block. You can also quickly check if the receiver was
                # stopped and let any other unexpected exceptions bubble up.
                if selected.was_stopped:
                    print("timer1 was stopped")
                    continue
                print(f"timer1: now={datetime.datetime.now()} drift={selected.message}")
                timer2.stop()
            elif selected_from(selected, timer2):
                # Explicitly handling of exceptions
                match selected.exception:
                    case ReceiverStoppedError():
                        print("timer2 was stopped")
                    case Exception() as exception:
                        print(f"timer2: exception={exception}")
                    case None:
                        # All good, no exception, we can use `selected.message` safely
                        print(f"timer2: now={datetime.datetime.now()} drift={selected.message}")
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
        BaseExceptionGroup: If there is an error while finishing the select operation
            and receivers fail while cleaning up.
        SelectError: If there is an error while selecting receivers during normal
            operation.  For example if a receiver raises an exception in the `ready()`
            method.  Normal errors while receiving messages are not raised, but reported
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
        BaseExceptionGroup: If the receivers raise any exceptions.
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
            raise BaseExceptionGroup(
                "Some receivers failed when select()ing", exceptions
            )
