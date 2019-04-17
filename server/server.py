#!/usr/bin/env python3

import connexion
from flask import Flask, jsonify
import sqlite3
import pathlib


app = Flask(__name__)
DATA_DIR = pathlib.Path('./data')


def query(log_id):
    path = DATA_DIR / f'{log_id}.sqlite'
    if not path.exists():
        return jsonify({'error': 'log not found'}), 404
    conn = sqlite3.connect(str(path))
    conn.enable_load_extension(True)
    conn.load_extension('/usr/lib/sqlite3/pcre.so')
    cursor = conn.cursor()

    filters_str = ''
    size = 5000
    offset = 0

    if filters_str:
        where_clause = 'WHERE ' + filters_str
    else:
        where_clause = ''

    q = f"SELECT line FROM logs {where_clause} LIMIT {size} OFFSET {offset}"
    return jsonify({"log_lines": '\n'.join([x[0] for x in cursor.execute(q).fetchall()])})


def _main():
    app = connexion.App(__name__, specification_dir='openapi/')
    app.add_api('api.yml')
    app.run(port=8080)


if __name__ == '__main__':
    _main()
