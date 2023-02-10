# License: MIT
# Copyright © 2022 Frequenz Energy-as-a-Service GmbH

"""Tests for the RequestResponse implementation."""

import asyncio

from frequenz.channels import Bidirectional


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
