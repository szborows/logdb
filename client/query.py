#!/usr/bin/env python3
import base64
import requests
import argparse
import json

def query(url, log, filters):
    if filters:
        filters_str = '?filters=' + b','.join(base64.b64encode(f.encode()) for f in filters).decode()
    else:
        filters_str = ''
    r = requests.get(f'{url}/api/v1/log/{log}/query{filters_str}')
    r.raise_for_status()
    print(r.json()['log_lines'])

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='http://127.0.0.1:8080')
    ap.add_argument('-f', '--filter', action='append')
    ap.add_argument('log')
    args = ap.parse_args()
    query(args.url, args.log, args.filter or [])
