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


app = Flask(__name__)
DATA_DIR = pathlib.Path('./data')
CONFIG_PATH = './config.yml'
DEFAULT_CONFIG = {
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


def _start(peers):
    print('peers:', peers)
    app = connexion.App(__name__, specification_dir='openapi/')
    app.add_api('api.yml')
    app.run(port=8080)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('peers', nargs='+')
    args = ap.parse_args()
    if os.path.isfile(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            config = yaml.load(f.read(), Loader=yaml.SafeLoader)
    else:
        config = DEFAULT_CONFIG
    _start(args.peers)
