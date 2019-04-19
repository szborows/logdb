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


app = Flask(__name__)
DATA_DIR = pathlib.Path('./data')
DEFAULT_CONFIG = {
    'network': {
        'bind': '127.0.0.1:8080'
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
    host, port = config['network']['bind'].split(':')
    app.run(host=host, port=port)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--config', default='config.yml')
    args = ap.parse_args()
    if os.path.isfile(args.config):
        with open(args.config) as f:
            config = {**DEFAULT_CONFIG, **yaml.load(f.read(), Loader=yaml.SafeLoader)}
    else:
        config = DEFAULT_CONFIG
    _start(config)
