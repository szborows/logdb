#!/usr/bin/env python3

import asyncio
import json
import logging


class LocalProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        super().__init__()
        self.on_ping, self.on_ping_req, self.on_ack = None, None, None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        request = json.loads(data)
        if request['type'] == 'ping':
            self.on_ping(self, addr, request)
        elif request['type'] == 'ping-req':
            self.on_ping_req(self, addr, request['target'], request)
        elif request['type'] == 'ack':
            self.on_ack(self, addr, request)
        else:
            logging.error('Received unknown request type: ' + str(request['type']))


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
    transport, net = await loop.create_datagram_endpoint(LocalProtocol, local_addr=('127.0.0.1', 9999))
    def on_ping(net, addr, data):
        seq = 0  # TODO
        net.transport.sendto(json.dumps({'type': 'ack', 'seq': seq}).encode(), addr)
    def on_ping_request(net, addr, target, data):
        seq = 0  # TODO
        self.transport.sendto(json.dumps({'type': 'ping', 'seq': seq}).encode(), target)
    def on_ack(net, addr, data):
        seq = 0  # TODO
        # must decide if this is ack from ping or ping-req
        print('ack received')
    net.on_ping = on_ping
    membership = Membership()
    asyncio.ensure_future(_run_disseminator(net, membership))
    asyncio.ensure_future(_run_failure_detector(net, membership))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_init(loop))
    loop.run_forever()
