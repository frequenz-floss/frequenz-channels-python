# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Benchmark for Anycast channels."""

import asyncio
import csv
import timeit
from typing import Any, Coroutine, Dict, List, Tuple

from frequenz.channels import Anycast, Receiver, Sender


async def send_msg(num_messages: int, chan: Sender[int]) -> None:
    """Send messages to the channel continuously.

    Args:
        num_messages (int): Number of messages to send.
        chan (Sender[int]): Channel sender to send the messages to.
    """
    # send one message for each receiver
    for ctr in range(num_messages):
        await chan.send(ctr + 1)


async def benchmark_anycast(
    num_channels: int,
    num_messages: int,
    num_receivers: int,
    buffer_size: int,
) -> int:
    """Ensure sent messages are received by one receiver.

    Args:
        num_channels (int): Number of channels to create.
        num_messages (int): Number of messages to send per channel.
        num_receivers (int): Number of broadcast receivers per channel.
        buffer_size (int): Buffer size of each channel.

    Returns:
        int: Total number of messages received by all channels.
    """
    channels: List[Anycast[int]] = [Anycast(buffer_size) for _ in range(num_channels)]
    senders = [
        asyncio.create_task(send_msg(num_messages, bcast.get_sender()))
        for bcast in channels
    ]

    # Even though we want just a single int, use a list, so that it can be
    # updated from other methods.
    recv_trackers = [0]

    async def update_tracker_on_receive(chan: Receiver[int]) -> None:
        while True:
            msg = await chan.receive()
            if msg is None:
                return
            recv_trackers[0] += 1

    receivers = []
    for acast in channels:
        for _ in range(num_receivers):
            receivers.append(update_tracker_on_receive(acast.get_receiver()))

    receivers_runs = asyncio.gather(*receivers)

    await asyncio.gather(*senders)
    for bcast in channels:
        await bcast.close()
    await receivers_runs
    return recv_trackers[0]


def time_async_task(task: Coroutine[Any, Any, int]) -> Tuple[float, Any]:
    """Run a task and return the time taken and the result.

    Args:
        task (asyncio.Task): Task to run.

    Returns:
        (float, Any): Run time in fractional seconds, task return value.
    """
    start = timeit.default_timer()
    ret = asyncio.run(task)
    return timeit.default_timer() - start, ret


def run_one(
    num_channels: int,
    num_messages: int,
    num_receivers: int,
    buffer_size: int,
) -> Dict[str, Any]:
    """Run a single benchmark."""
    runtime, total_msgs = time_async_task(
        benchmark_anycast(num_channels, num_messages, num_receivers, buffer_size)
    )
    ret = {
        "channels": num_channels,
        "messages_per_channel": num_messages,
        "receivers": num_receivers,
        "buffer_size": buffer_size,
        "total_messages": total_msgs,
        "runtime": f"{runtime:.3f}",
    }

    return ret


def run() -> None:
    """Run all benchmarks."""
    with open("/dev/stdout", "w", encoding="utf-8") as csvfile:
        fields = run_one(1, 0, 1, 1)
        out = csv.DictWriter(csvfile, fields.keys())
        out.writeheader()
        out.writerow(run_one(1, 1000000, 1, 100))
        out.writerow(run_one(1, 1000000, 1, 1000))
        out.writerow(run_one(1, 1000000, 10, 100))
        out.writerow(run_one(1, 1000000, 10, 1000))
        out.writerow(run_one(1000, 1000, 1, 100))
        out.writerow(run_one(1000, 1000, 1, 1000))
        out.writerow(run_one(1000, 1000, 10, 100))
        out.writerow(run_one(1000, 1000, 10, 1000))


if __name__ == "__main__":
    run()
