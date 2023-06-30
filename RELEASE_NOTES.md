# Frequenz Channels Release Notes

## Summary

The minimum Python supported version was bumped to 3.11 and the `Select` class replaced by the new `select()` function.

## Upgrading

* The minimum supported Python version was bumped to 3.11, downstream projects will need to upgrade too to use this version.

* The `Select` class was replaced by a new `select()` function, with the following improvements:

  * Type-safe: proper type hinting by using the new helper type guard `selected_from()`.
  * Fixes potential starvation issues.
  * Simplifies the interface by providing values one-by-one.
  * Guarantees there are no dangling tasks left behind when used as an async context manager.

  This new function is an [async iterator](https://docs.python.org/3.11/library/collections.abc.html#collections.abc.AsyncIterator), and makes sure no dangling tasks are left behind after a select loop is done.

  Example:
  ```python
  timer1 = Timer.periodic(datetime.timedelta(seconds=1))
  timer2 = Timer.timeout(datetime.timedelta(seconds=0.5))

  async for selected in select(timer1, timer2):
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

## New Features

* A new `select()` function was added, please look at the *Upgrading* section for details.

* A new `Event` utility receiver was added.

  This receiver can be made ready manually.  It is mainly useful for testing but can also become handy in scenarios where a simple, on-off signal needs to be sent to a select loop for example.

  Example:

  ```python
  import asyncio
  from frequenz.channels import Receiver
  from frequenz.channels.util import Event, select, selected_from

  other_receiver: Receiver[int] = ...
  exit_event = Event()

  async def exit_after_10_seconds() -> None:
      asyncio.sleep(10)
      exit_event.set()

  asyncio.ensure_future(exit_after_10_seconds())

  async for selected in select(exit_event, other_receiver):
      if selected_from(selected, exit_event):
          break
      if selected_from(selected, other_receiver):
          print(selected.value)
      else:
          assert False, "Unknow receiver selected"
  ```

* The `Timer` class now has more descriptive `__str__` and `__repr__` methods.
