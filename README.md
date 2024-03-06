# Frequenz channels

[![Build Status](https://github.com/frequenz-floss/frequenz-channels-python/actions/workflows/ci.yaml/badge.svg)](https://github.com/frequenz-floss/frequenz-channels-python/actions/workflows/ci.yaml)
[![PyPI Package](https://img.shields.io/pypi/v/frequenz-channels)](https://pypi.org/project/frequenz-channels/)
[![Docs](https://img.shields.io/badge/docs-latest-informational)](https://frequenz-floss.github.io/frequenz-channels-python/)

## Introduction

<!-- introduction -->

Frequenz Channels is a *channels* implementation for Python.

According to [Wikipedia](https://en.wikipedia.org/wiki/Channel_(programming)):

> A channel is a model for interprocess communication and synchronization via
> message passing. A message may be sent over a channel, and another process or
> thread is able to receive messages sent over a channel it has a reference to,
> as a stream. Different implementations of channels may be buffered or not,
> and either synchronous or asynchronous.

Frequenz Channels are mostly designed after [Go
channels](https://tour.golang.org/concurrency/2) but it also borrows ideas from
[Rust channels](https://doc.rust-lang.org/book/ch16-02-message-passing.html).

<!-- /introduction -->

## Supported Platforms

<!-- supported-platforms -->

The following platforms are officially supported (tested):

- **Python:** 3.11
- **Operating System:** Ubuntu Linux 20.04
- **Architectures:** amd64, arm64

> [!NOTE]
> Newer Python versions and other operating systems and architectures might
> work too, but they are not automatically tested, so we cannot guarantee it.

<!-- /supported-platforms -->

## Quick Start

### Installing

<!-- quick-start-installing -->

Assuming a [supported](#supported-platforms) working Python environment:

```sh
python3 -m pip install frequenz-channels
```

> [!TIP]
> For more details please read the [Installation
> Guide](docs/user-guide/installation.md).

<!-- /quick-start-installing -->

### Examples

#### Hello World

<!-- quick-start-hello-world -->

```python
import asyncio

from frequenz.channels import Anycast


async def main() -> None:
    hello_channel = Anycast[str](name="hello-world-channel")
    sender = hello_channel.new_sender()
    receiver = hello_channel.new_receiver()

    await sender.send("Hello World!")
    message = await receiver.receive()
    print(message)


asyncio.run(main())
```

<!-- /quick-start-hello-world -->

#### Showcase

<!-- quick-start-showcase -->

This is a comprehensive example that shows most of the main features of the
library:

```python
import asyncio
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum, auto
from typing import assert_never

from frequenz.channels import (
    Anycast,
    Broadcast,
    Receiver,
    Sender,
    merge,
    select,
    selected_from,
)
from frequenz.channels.timer import SkipMissedAndDrift, Timer, TriggerAllMissed


class Command(Enum):
    PING = auto()
    STOP_SENDER = auto()


class ReplyCommand(Enum):
    PONG = auto()


@dataclass(frozen=True)
class Reply:
    reply: ReplyCommand
    source: str


async def send(
    sender: Sender[str],
    control_command: Receiver[Command],
    control_reply: Sender[Reply],
) -> None:
    """Send a counter value every second, until a stop command is received."""
    print(f"{sender}: Starting")
    timer = Timer(timedelta(seconds=1.0), TriggerAllMissed())
    counter = 0
    async for selected in select(timer, control_command):
        if selected_from(selected, timer):
            print(f"{sender}: Sending {counter}")
            await sender.send(f"{sender}: {counter}")
            counter += 1
        elif selected_from(selected, control_command):
            print(f"{sender}: Received command: {selected.message.name}")
            match selected.message:
                case Command.STOP_SENDER:
                    print(f"{sender}: Stopping")
                    break
                case Command.PING:
                    print(f"{sender}: Ping received, reply with pong")
                    await control_reply.send(Reply(ReplyCommand.PONG, str(sender)))
                case _ as unknown:
                    assert_never(unknown)
    print(f"{sender}: Finished")


async def receive(
    receivers: list[Receiver[str]],
    control_command: Receiver[Command],
    control_reply: Sender[Reply],
) -> None:
    """Receive data from multiple channels, until no more data is received for 2 seconds."""
    print("receive: Starting")
    timer = Timer(timedelta(seconds=2.0), SkipMissedAndDrift())
    print(f"{timer=}")
    merged = merge(*receivers)
    async for selected in select(merged, timer, control_command):
        if selected_from(selected, merged):
            message = selected.message
            print(f"receive: Received {message=}")
            timer.reset()
            print(f"{timer=}")
        elif selected_from(selected, control_command):
            print(f"receive: received command: {selected.message.name}")
            match selected.message:
                case Command.PING:
                    print("receive: Ping received, reply with pong")
                    await control_reply.send(Reply(ReplyCommand.PONG, "receive"))
                case Command.STOP_SENDER:
                    pass  # Ignore
                case _ as unknown:
                    assert_never(unknown)
        elif selected_from(selected, timer):
            drift = selected.message
            print(
                f"receive: No data received for {timer.interval + drift} seconds, "
                "giving up"
            )
            break
    print("receive: Finished")


async def main() -> None:
    data_channel_1 = Anycast[str](name="data-channel-1")
    data_channel_2 = Anycast[str](name="data-channel-2")
    command_channel = Broadcast[Command](name="control-channel")  # (1)!
    reply_channel = Anycast[Reply](name="reply-channel")

    async with asyncio.TaskGroup() as tasks:
        tasks.create_task(
            send(
                data_channel_1.new_sender(),
                command_channel.new_receiver(),
                reply_channel.new_sender(),
            ),
            name="send-channel-1",
        )
        tasks.create_task(
            send(
                data_channel_2.new_sender(),
                command_channel.new_receiver(),
                reply_channel.new_sender(),
            ),
            name="send-channel-2",
        )
        tasks.create_task(
            receive(
                [data_channel_1.new_receiver(), data_channel_2.new_receiver()],
                command_channel.new_receiver(),
                reply_channel.new_sender(),
            ),
            name="receive",
        )

        control_sender = command_channel.new_sender()
        reply_receiver = reply_channel.new_receiver()

        # Send a ping command to all tasks and wait for the replies
        await control_sender.send(Command.PING)
        print(f"main: {await reply_receiver.receive()}")
        print(f"main: {await reply_receiver.receive()}")
        print(f"main: {await reply_receiver.receive()}")

        await asyncio.sleep(5.0)

        # Stop senders, after 2 seconds not receiving any data,
        # the receiver will stop too
        await control_sender.send(Command.STOP_SENDER)


asyncio.run(main())
```

<!-- /quick-start-showcase -->

## Documentation

For more information, please read the [documentation
website](https://frequenz-floss.github.io/frequenz-channels-python/).

## Contributing

If you want to know how to build this project and contribute to it, please
check out the [Contributing Guide](docs/CONTRIBUTING.md).
