# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the RequestResponse implementation."""

import asyncio

import pytest

from frequenz.channels import (
    Bidirectional,
    ChannelClosedError,
    ChannelError,
    ReceiverError,
    SenderError,
)


async def test_request_response() -> None:
    """Ensure bi-directional communication is possible."""

    req_resp: Bidirectional[int, str] = Bidirectional("test_client", "test_service")

    async def service(handle: Bidirectional.Handle[str, int]) -> None:
        while True:
            num = await handle.receive()
            if num is None:
                break
            if num == 42:
                break
            if num >= 0:
                await handle.send("positive")
            else:
                await handle.send("negative")

    service_task = asyncio.create_task(
        service(req_resp.service_handle),
    )

    client_handle: Bidirectional.Handle[int, str] = req_resp.client_handle

    for ctr in range(-5, 5):
        await client_handle.send(ctr)
        ret = await client_handle.receive()
        if ctr < 0:
            assert ret == "negative"
        else:
            assert ret == "positive"

    await client_handle.send(42)  # Stop the service task
    await service_task


async def test_sender_error_chaining() -> None:
    """Ensure bi-directional communication is possible."""

    req_resp: Bidirectional[int, str] = Bidirectional("test_client", "test_service")

    await req_resp._response_channel.close()  # pylint: disable=protected-access

    with pytest.raises(SenderError, match="The channel was closed") as exc_info:
        await req_resp.service_handle.send("I'm closed!")

    err = exc_info.value
    cause = err.__cause__
    assert isinstance(cause, ChannelError)
    assert cause.args[0].startswith("Error in the underlying channel")
    assert isinstance(cause.__cause__, ChannelClosedError)


async def test_ready_error_chaining() -> None:
    """Ensure bi-directional communication is possible."""

    req_resp: Bidirectional[int, str] = Bidirectional("test_client", "test_service")

    await req_resp._request_channel.close()  # pylint: disable=protected-access

    with pytest.raises(ReceiverError, match="Receiver .* was stopped") as exc_info:
        await req_resp.service_handle.ready()

    err = exc_info.value
    cause = err.__cause__
    assert isinstance(cause, ChannelError)
    assert cause.args[0].startswith("Error in the underlying channel")
    assert isinstance(cause.__cause__, ChannelClosedError)
