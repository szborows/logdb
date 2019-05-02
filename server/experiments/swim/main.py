#!/usr/bin/env python3

import asyncio


class MyProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print(data)

async def _run_controller():
    while True:
        await asyncio.sleep(1)
        print('alive')

async def _init(loop):
    await loop.create_datagram_endpoint(MyProtocol,local_addr=('127.0.0.1', 9999))
    asyncio.ensure_future(_run_controller())

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_init(loop))
    loop.run_forever()
