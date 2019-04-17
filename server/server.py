#!/usr/bin/env python3

import connexion
from flask import Flask, jsonify


app = Flask(__name__)


def query(log_id):
    return jsonify({'hello': 'world'})


def _main():
    app = connexion.App(__name__, specification_dir='openapi/')
    app.add_api('api.yml')
    app.run(port=8080)


if __name__ == '__main__':
    _main()
