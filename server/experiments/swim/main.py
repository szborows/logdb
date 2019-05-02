#!/usr/bin/env python3

import asyncio


class MyProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        super().__init__()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print(data)

async def _init():
    await loop.create_datagram_endpoint(MyProtocol,local_addr=('127.0.0.1', 9999))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_init())
    loop.run_forever()
