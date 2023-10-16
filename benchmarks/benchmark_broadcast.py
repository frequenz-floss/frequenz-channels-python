# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Benchmark for Broadcast channels."""

import asyncio
import csv
import timeit
from collections.abc import Callable, Coroutine
from functools import partial
from typing import Any

from frequenz.channels import Broadcast, Receiver, Sender


async def component_sender(num_messages: int, chan: Sender[int]) -> None:
    """Send a message to the channel every 0.2 seconds.

    Args:
        num_messages (int): Number of messages to send.
        chan (Sender[int]): Channel sender to send the messages to.
    """
    for ctr in range(num_messages):
        await chan.send(ctr)
        await asyncio.sleep(0.2)


async def fast_sender(num_messages: int, chan: Sender[int]) -> None:
    """Send messages to the channel continuously.

    Args:
        num_messages (int): Number of messages to send.
        chan (Sender[int]): Channel sender to send messages to.
    """
    for ctr in range(num_messages):
        await chan.send(ctr)
        # When there is a continuous stream of messages, the asyncio scheduler
        # doesn't appear to be "Completely Fair" to the receiver tasks,
        # especially when there are a lot of receivers and few senders, and
        # without a periodic break in the sender, the receivers are lagging
        # behind.
        if ctr % 50 == 0:
            await asyncio.sleep(0.0)


async def benchmark_broadcast(
    send_msg: Callable[[int, Sender[int]], Coroutine[Any, Any, None]],
    num_channels: int,
    num_messages: int,
    num_receivers: int,
) -> int:
    """Benchmark with senders and receivers running in separate tasks.

    Args:
        send_msg (Callable): Method to use as sender (component_sender or
            fast_sender).
        num_channels (int): Number of channels to create.
        num_messages (int): Number of messages to send per channel.
        num_receivers (int): Number of broadcast receivers per channel.

    Returns:
        int: Total number of messages received by all receivers.
    """
    channels: list[Broadcast[int]] = [Broadcast("meter") for _ in range(num_channels)]
    senders: list[asyncio.Task[Any]] = [
        asyncio.create_task(send_msg(num_messages, bcast.new_sender()))
        for bcast in channels
    ]

    recv_trackers = [0]

    async def update_tracker_on_receive(chan: Receiver[int]) -> None:
        async for _ in chan:
            recv_trackers[0] += 1

    receivers = []
    for bcast in channels:
        for _ in range(num_receivers):
            receivers.append(update_tracker_on_receive(bcast.new_receiver()))

    receivers_runs = asyncio.gather(*receivers)

    await asyncio.gather(*senders)
    for bcast in channels:
        await bcast.close()
    await receivers_runs
    recv_tracker = sum(recv_trackers)
    assert recv_tracker == num_messages * num_channels * num_receivers
    return recv_tracker


async def benchmark_single_task_broadcast(
    num_channels: int,
    num_messages: int,
    num_receivers: int,
) -> int:
    """Benchmark with senders and receivers invoked from the same task.

    Args:
        num_channels (int): number of channels to create.
        num_messages (int): number of messages to send per channel.
        num_receivers (int): number of broadcast receivers per channel.

    Returns:
        int: Total number of messages received by all receivers.
    """
    channels: list[Broadcast[int]] = [Broadcast("meter") for _ in range(num_channels)]
    senders = [b.new_sender() for b in channels]
    recv_tracker = 0

    receivers = [
        [bcast.new_receiver() for _ in range(num_receivers)] for bcast in channels
    ]

    for ctr in range(num_messages):
        for sender in senders:
            await sender.send(ctr)
        for recv_list in receivers:
            for recv in recv_list:
                _ = await recv.receive()
                recv_tracker += 1
    assert recv_tracker == num_messages * num_channels * num_receivers
    return recv_tracker


def time_async_task(task: Coroutine[Any, Any, int]) -> tuple[float, Any]:
    """Run a task and return the time taken and the result.

    Args:
        task (asyncio.Task): Task to run.

    Returns:
        (float, Any): Run time in fractional seconds, task return value.
    """
    start = timeit.default_timer()
    ret = asyncio.run(task)
    return timeit.default_timer() - start, ret


# pylint: disable=too-many-arguments
def run_one(
    benchmark_method: Callable[[int, int, int], Coroutine[Any, Any, int]],
    num_channels: int,
    num_messages: int,
    num_receivers: int,
    tasks_used: str,
    interval_between_messages: float,
) -> dict[str, Any]:
    """Run a single benchmark."""
    runtime, total_msgs = time_async_task(
        benchmark_method(num_channels, num_messages, num_receivers)
    )
    ret = {
        "channels": num_channels,
        "messages_per_channel": num_messages,
        "receivers": num_receivers,
        "interval_between_messages": interval_between_messages,
        "total_messages": total_msgs,
        "tasks_used": tasks_used,
        "runtime": f"{runtime:.3f}",
    }

    return ret


def run() -> None:
    """Run all benchmarks."""
    component_sender_benchmark = partial(benchmark_broadcast, component_sender)
    fast_sender_benchmark = partial(benchmark_broadcast, fast_sender)
    with open("/dev/stdout", "w", encoding="utf-8") as csvfile:
        fields = run_one(component_sender_benchmark, 1, 0, 1, "", 0.0)
        out = csv.DictWriter(csvfile, list(fields.keys()))
        out.writeheader()
        out.writerow(run_one(component_sender_benchmark, 10, 10, 10, "multiple", 0.2))
        out.writerow(run_one(component_sender_benchmark, 100, 10, 10, "multiple", 0.2))
        out.writerow(run_one(component_sender_benchmark, 100, 10, 100, "multiple", 0.2))
        out.writerow(run_one(component_sender_benchmark, 1000, 10, 10, "multiple", 0.2))
        out.writerow(run_one(fast_sender_benchmark, 10, 100, 1000, "multiple", 0.0))
        out.writerow(run_one(fast_sender_benchmark, 100, 100, 100, "multiple", 0.0))
        out.writerow(
            run_one(benchmark_single_task_broadcast, 10, 100, 1000, "single", 0.0)
        )
        out.writerow(
            run_one(benchmark_single_task_broadcast, 100, 100, 100, "single", 0.0)
        )


if __name__ == "__main__":
    run()
