#!/usr/bin/env python3

import socket
import argparse
import json

def _main(args):
    if args.command == 'ping':
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(json.dumps({"type": "ping"}).encode(), ('127.0.0.1', 9999))
    else:
        raise NotImplementedError()

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('command')
    args = ap.parse_args()
    _main(args)
