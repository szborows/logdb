#!/usr/bin/env python3

import asyncio
import json


class MyProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print(json.loads(data))

# TODO: should support iteration, dict-like interface or equivalent
class Membership:
    def __init__(self):
        self.members = []

async def _run_disseminator(net, membership):
    while True:
        await asyncio.sleep(1)

async def _run_failure_detector(net, membership):
    interval = 20
    ping_timeout = 4
    ping_req_timeout = 12
    ping_req_group_size = 3
    while True:
        await asyncio.sleep(1)

async def _init(loop):
    net = await loop.create_datagram_endpoint(MyProtocol, local_addr=('127.0.0.1', 9999))
    membership = Membership()
    asyncio.ensure_future(_run_disseminator(net, membership))
    asyncio.ensure_future(_run_failure_detector(net, membership))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_init(loop))
    loop.run_forever()
