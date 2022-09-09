"""Tests for the RequestResponse implementation.

Copyright
Copyright © 2022 Frequenz Energy-as-a-Service GmbH

License
MIT
"""

import asyncio

from frequenz.channels import Bidirectional, BidirectionalHandle


async def test_request_response() -> None:
    """Ensure bi-directional communication is possible."""

    req_resp: Bidirectional[int, str] = Bidirectional("test_client", "test_service")

    async def service(handle: BidirectionalHandle[str, int]) -> None:
        while True:
            num = await handle.receive()
            if num is None:
                break
            if num >= 0:
                await handle.send("positive")
            else:
                await handle.send("negative")

    asyncio.create_task(
        service(req_resp.service_handle),
    )

    client_handle: BidirectionalHandle[int, str] = req_resp.client_handle

    for ctr in range(-5, 5):
        await client_handle.send(ctr)
        ret = await client_handle.receive()
        if ctr < 0:
            assert ret == "negative"
        else:
            assert ret == "positive"
