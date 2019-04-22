#!/usr/bin/env python3

from aiohttp import web
import aiohttp
import aiohttp_autoreload
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
from functools import wraps

from utils import merge_dicts


class RaftState:
    FOLLOWER = 0
    CANDIDATE = 1
    LEADER = 2


class LocalLogs:
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

    def add_logs(self, local_logs):
        self._local_logs = local_logs

    def sync(self):
        logging.info('Syncing cluster state')
        self._syncObjConf = SyncObjConf(
            onReady=lambda: self._onReady(),
            onStateChanged=lambda os, ns: self._stateChanged(os, ns)
        )
        self._syncObj = SyncObj(
            f'{self._addr}:{self._raft_port}',
            [f'{p}:{self._raft_port}' for p in self._peers],
            consumers=[self._logs],
            conf=self._syncObjConf
        )

    def _onReady(self):
        logging.info(f'Raft ready...')
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

    def healthy(self):
        logging.info(json.dumps(self._syncObj.getStatus(), indent=2))
        return self._syncObj.getStatus()['leader'] is not None


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


async def query_local(request, log_id, filters):
    path = request.app['data_dir'] / f'{log_id}.sqlite'
    if not path.exists():
        return web.json_response({'error': 'data inconsistency at node'}, status=500)
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
    logging.info('Q: ' + q)
    return web.json_response({"log_lines": '\n'.join([x[0] for x in cursor.execute(q).fetchall()])})


async def query_remote(config, cluster, log_id, filters):
    node = cluster.state()['logs'].get(log_id)
    if node is None:
        return web.json_response({'error': 'log not found in cluster'}, status=404)
    logging.info('Found node which holds requested log: ' + node)
    # streaming HTTP could possibly be used too, but with current assumptions 1 line is up to
    # 513 bytes, and 15k is expected number of lines fetched. that gives 7.5MB. Not too bad.

    if filters:
        filters_str = '?filters=' + ','.join(filters)
    else:
        filters_str = ''

    try:
        async with aiohttp.ClientSession(raise_for_status=True) as client:
            port = config['network']['app_port']
            url = f'http://{node}:{port}/api/v1/log/{log_id}/query{filters_str}'
            response = await client.get(url)
            return web.json_response(await response.json())
    except aiohttp.ClientResponseError as e:
        logging.warning('FAAAIL: ' + str(e))

    return web.json_response({'found log on other node...': 'xD'})


def ensure_cluster_healthy(fn):
    @wraps(fn)
    async def wrapper(**kwargs):
        cluster = kwargs.get('request').app['cluster']
        if not cluster.healthy():
            raise web.HTTPServiceUnavailable()
        return await fn(**kwargs)
    return wrapper


@ensure_cluster_healthy
async def create(request, log_id):
    if log_id in request.app['local_logs'].logs:
        raise web.HTTPConflict()
    # race condition possible?
    if log_id in request.app['cluster'].state()['logs']:
        raise web.HTTPConflict()
    logging.info('should create new log: ' + log_id)
    return web.Response()


@ensure_cluster_healthy
async def query(request, log_id, filters=None):
    filters = filters or []

    if log_id in request.app['local_logs'].logs:
        logging.info('Query: found local log')
        return await query_local(request, log_id, filters)
    else:
        logging.info('Query: local log not found...')
        return await query_remote(request.app['config'], request.app['cluster'], log_id, filters)


async def dev_cluster_state(request):
    cluster = request.app['cluster']
    return web.json_response(cluster.state())


def _start(config):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [{name}] %(message)s'.format(name=config['node']['name'])
    )

    logging.info('config: ' + json.dumps(config, indent=2))

    app = connexion.AioHttpApp(__name__, specification_dir='openapi/')
    api = app.add_api('api.yml', pass_context_arg_name='request')
    local_logs = LocalLogs(config['data_dir'])
    cluster = Cluster(config['network']['bind'], config['network']['peers'])
    cluster.add_logs(local_logs)
    cluster.sync()
    api.subapp['config'] = config
    api.subapp['cluster'] = cluster
    api.subapp['data_dir'] = pathlib.Path(config['data_dir'])
    api.subapp['local_logs'] = local_logs

    host = config['network']['bind']
    aiohttp_autoreload.start()
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
