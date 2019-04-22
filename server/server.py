#!/usr/bin/env python3

from aiohttp import web
import argparse
import copy
import json
import connexion
import sqlite3
import pathlib
import base64
import logging
import yaml
import os
import random
import string
from pysyncobj import SyncObj, SyncObjConf
from pysyncobj.batteries import ReplCounter, ReplDict

from utils import merge_dicts


class RaftState:
    FOLLOWER = 0
    CANDIDATE = 1
    LEADER = 2


class Logs:
    def __init__(self, data_dir):
        self.logs = []
        logging.info('Finding logs on local filesystem')
        for entry in os.listdir(data_dir):
            path = os.path.join(data_dir, entry)
            log_name, ext = os.path.splitext(entry)
            if ext != '.sqlite':
                continue
            self.logs.append(log_name)
        if self.logs:
            logging.info('Found following logs on local filesystem: ' + ', '.join(self.logs))
        else:
            logging.info('Found no logs on local filesystem')

class Cluster:
    def __init__(self, addr, peers):
        self._addr = addr
        self._peers = peers
        self.nodes = [self._addr] + self._peers
        self._logs = ReplDict()
        self._raft_port = config['network']['raft_port']

    def set_logs(self, logs):
        self._local_logs = logs

    def sync(self):
        logging.info('Syncing cluster state')
        self._syncObjConf = SyncObjConf(
            onReady=lambda: self._onReady(),
            onStateChanged=lambda os, ns: self._stateChanged(os, ns)
        )
        self._syncObj = SyncObj(f'{self._addr}:{self._raft_port}', [f'{p}:{self._raft_port}' for p in self._peers], consumers=[self._logs], conf=self._syncObjConf)

    def _onReady(self):
        logging.info(f'Raft ready...')
        #import time; time.sleep(5)
        logging.info(json.dumps(self._syncObj.getStatus(), indent=2))
        if self._local_logs.logs:
            logging.info('sending info about local logs')
        # it still doesn't support log replicas...
        for log in self._local_logs.logs:
            logging.warning(log)
            self._logs.set(log, self._addr)

    def _stateChanged(self, oldState, newState):
        if newState == RaftState.FOLLOWER:
            state = 'follower'
        elif newState == RaftState.CANDIDATE:
            state = 'candidate'
        else:
            state = 'leader'
        logging.info(f'changed Raft role to: {state}')

    def state(self):
        return {
            'logs': copy.copy(self._logs.rawData())
        }


DEFAULT_CONFIG = {
    'network': {
        'bind': '127.0.0.1',
        'app_port': 8080,
        'raft_port': 4321
    },
    'node': {
        'name': ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(12)])
    },
    'data_dir': './data'
}

async def query(request, log_id, filters=None):
    filters = filters or []
    path = request.app['data_dir'] / f'{log_id}.sqlite'
    if not path.exists():
        return web.json_response({'error': 'log not found'}, status=404)
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

    q = f"SELECT line FROM logs {where_clause} LIMIT {size} OFFSET {offset}"
    return web.json_response({"log_lines": '\n'.join([x[0] for x in cursor.execute(q).fetchall()])})

async def dev_cluster_state(request):
    cluster = request.app['cluster']
    #logging.info(json.dumps(cluster._syncObj.getStatus(), indent=2))
    #cluster.state().set('k', {'nk': 'v'}, sync=True)
    return web.json_response(cluster.state())


def _start(config):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [{name}] %(message)s'.format(name=config['node']['name']))

    logging.info('config:' + json.dumps(config, indent=2))

    app = connexion.AioHttpApp(__name__, specification_dir='openapi/')
    api = app.add_api('api.yml', pass_context_arg_name='request')
    logs = Logs(config['data_dir'])
    cluster = Cluster(config['network']['bind'], config['network']['peers'])
    cluster.set_logs(logs)
    cluster.sync()
    api.subapp['cluster'] = cluster
    api.subapp['data_dir'] = pathlib.Path(config['data_dir'])
    api.subapp['logs'] = logs 

    host = config['network']['bind']
    app.run(host=host, port=config['network']['app_port'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-c', '--config', default='config.yml')
    args = ap.parse_args()
    if os.path.isfile(args.config):
        with open(args.config) as f:
            config = merge_dicts(DEFAULT_CONFIG, yaml.load(f.read(), Loader=yaml.SafeLoader))
    else:
        config = DEFAULT_CONFIG
    _start(config)
