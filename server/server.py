#!/usr/bin/env python3

import argparse
import connexion
from flask import Flask, jsonify
import sqlite3
import pathlib
import base64
import logging
import yaml
import os
import random
import string
from pysyncobj import SyncObj
from pysyncobj.batteries import ReplCounter, ReplDict

from utils import merge_dicts

class Cluster:
    def __init__(self, addr, peers):
        self.nodes = [addr] + peers
        self._state = ReplDict()
        self._syncObj = SyncObj(addr, ['{0}:{1}'.format(p, config['network']['raft_port']) for p in peers] ['serverB:4321', 'serverC:4321'], consumers=[CLUSTER_STATE])


app = Flask(__name__)
DATA_DIR = pathlib.Path('./data')
DEFAULT_CONFIG = {
    'network': {
        'bind': '127.0.0.1',
        'app_port': 8080,
        'raft_port': 4321
    },
    'node': {
        'name': ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(12)])
    }
}

def query(log_id, filters=None):
    filters = filters or []
    path = DATA_DIR / f'{log_id}.sqlite'
    if not path.exists():
        return jsonify({'error': 'log not found'}), 404
    conn = sqlite3.connect(str(path))
    conn.enable_load_extension(True)
    conn.load_extension('/usr/lib/sqlite3/pcre.so')
    cursor = conn.cursor()

    filters_str = ' AND '.join(['line REGEXP "' + base64.b64decode(f).decode() + '"' for f in filters])
    size = 5000
    offset = 0

    if filters_str:
        where_clause = 'WHERE ' + filters_str
    else:
        where_clause = ''

    print(where_clause)

    q = f"SELECT line FROM logs {where_clause} LIMIT {size} OFFSET {offset}"
    return jsonify({"log_lines": '\n'.join([x[0] for x in cursor.execute(q).fetchall()])})


def _start(config):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [{name}] %(message)s'.format(name=config['node']['name']))
    print('config:', config)
    app = connexion.App(__name__, specification_dir='openapi/')
    app.add_api('api.yml')
    host = config['network']['bind']
    app.run(host=host, port=config['network']['app_port'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--config', default='config.yml')
    args = ap.parse_args()
    if os.path.isfile(args.config):
        with open(args.config) as f:
            config = merge_dicts(yaml.load(f.read(), Loader=yaml.SafeLoader), DEFAULT_CONFIG)
    else:
        config = DEFAULT_CONFIG
    _start(config)
