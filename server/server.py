#!/usr/bin/env python3

from aiohttp import web
import aiohttp
import aiohttp_autoreload
import argparse
import json
import tempfile
import sqlite3
import pathlib
import base64
import logging
import yaml
import os
import random
import string
from functools import wraps

from utils import merge_dicts
from cluster import Cluster

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

    def add(self, name):
        self.logs.append(name)


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


async def cluster_status(request):
    cluster = request.app['cluster']
    return web.json_response({
        'healthy': cluster.healthy(),
        'nodes': cluster.nodes.get_nodes()
    })


async def query_local(request, log_id, filters):
    path = request.app['data_dir'] / f'{log_id}.sqlite'
    if not path.exists():
        return web.json_response({'error': 'data inconsistency at node'}, status=500)
    conn = sqlite3.connect(str(path))
    conn.enable_load_extension(True)
    conn.load_extension('/usr/lib/sqlite3/pcre.so')
    cursor = conn.cursor()

    filters = [base64.b64decode(f).decode() for f in filters]
    filters_str = ' AND '.join(['line REGEXP "' + f + '"' for f in filters])
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
    log_info = cluster.logs.get_log(log_id)
    if log_info is None:
        return web.json_response({'error': 'log not found in cluster'}, status=404)
    # TODO: should not pick first one!
    log_replica_node = log_info['replicas'][0]
    logging.info('Found node which holds requested log: ' + log_replica_node)
    # streaming HTTP could possibly be used too, but with current assumptions 1 line is up to
    # 513 bytes, and 15k is expected number of lines fetched. that gives 7.5MB. Not too bad.

    if filters:
        filters_str = '?filters=' + ','.join(filters)
    else:
        filters_str = ''

    try:
        async with aiohttp.ClientSession(raise_for_status=True) as client:
            port = config['network']['app_port']
            url = f'http://{log_replica_node}:{port}/api/v1/log/{log_id}/query{filters_str}'
            response = await client.get(url)
            return web.json_response(await response.json())
    except aiohttp.ClientResponseError as e:
        logging.warning('FAAAIL: ' + str(e))

    return web.json_response({'found log on other node...': 'xD'})


def ensure_cluster_healthy(fn):
    @wraps(fn)
    async def wrapper(request, **kwargs):
        cluster = request.app['cluster']
        if not cluster.healthy():
            raise web.HTTPServiceUnavailable()
        return await fn(request, **kwargs)
    return wrapper


async def create_log(log_id, read_chunk_fn, output_path):
    size = 0
    with tempfile.NamedTemporaryFile() as tf:
        while True:
            chunk = await read_chunk_fn()
            if not chunk:
                break
            tf.write(chunk)
        tf.flush()

        if output_path.exists():
            raise RuntimeError(f'file {output_path} already exists!')

        conn = sqlite3.connect(str(output_path))
        cur = conn.cursor()

        CREATE_TABLE = '''
            CREATE TABLE logs (
                tags varchar(255),
                labels varchar(512),
                timestamp int,
                line text NOT NULL
            );
        '''
        cur.execute(CREATE_TABLE)

        with open(tf.name) as f:
            for line in f:
                j = json.loads(line)
                tags, labels, timestamp, line = ','.join(j['tags']), ','.join(j['labels']), j['timestamp'], j['line']
                cur.execute(
                    f'INSERT INTO logs (tags, labels, timestamp, line) VALUES '
                    f'("{tags}", "{labels}", "{timestamp}", "{line}")'
                )
            conn.commit()
        conn.close()


@ensure_cluster_healthy
async def create(request):
    log_id = request.match_info['log_id']
    if log_id in request.app['local_logs'].logs:
        raise web.HTTPConflict()
    # race condition possible?
    if log_id in request.app['cluster'].logs.get_logs():
        raise web.HTTPConflict()
    logging.info('should create new log: ' + log_id)

    # lot of stuff is not handled in this endpoint:
    # - file should not be created on disk
    # - backpressure is not handled
    # - retry is AFAIK not possible

    reader = await request.multipart()
    field = await reader.next()

    if field.name != 'file':
        raise web.HTTPBadRequest(body=b'request should contain a file named "file"')

    output_path = pathlib.Path(request.app['config']['data_dir']) / f'{log_id}.sqlite'
    await create_log(log_id, field.read_chunk, output_path)
    request.app['local_logs'].add(log_id)
    request.app['cluster'].sync_logs()
    # read_chunk uses 8192 bytes by default...

    return web.Response()


@ensure_cluster_healthy
async def replicate_log(request):
    log_id = request.match_info['log_id']
    logging.info(f'received request to replicate log {log_id}')
    return web.json_response({'acknowledged': True})


@ensure_cluster_healthy
async def list_logs(request):
    return web.json_response(request.app['cluster'].logs.get_logs())


@ensure_cluster_healthy
async def list_nodes(request):
    return web.json_response(request.app['cluster'].nodes.get_nodes())


@ensure_cluster_healthy
async def query(request):
    log_id = request.match_info['log_id']
    filters = request.query.get('filters', '').split(',')

    if log_id in request.app['local_logs'].logs:
        logging.info('Query: found local log')
        return await query_local(request, log_id, filters)
    else:
        logging.info('Query: local log not found...')
        return await query_remote(request.app['config'], request.app['cluster'], log_id, filters)


@ensure_cluster_healthy
async def log_status(request):
    log_id = request.match_info['log_id']
    return web.json_response(request.app['cluster'].logs.get_log(log_id))
    # TODO: implementation goes here
    #        - ad-hoc query SQLite local/remote?
    #        - store value in Raft?


@ensure_cluster_healthy
async def dev_readonly(request):
    pd = await request.post()
    if 'readonly' not in pd or pd['readonly'] not in ('true', 'false'):
        raise web.HTTPBadRequest()
    request.app['cluster'].local_msg(['set-readwrite', 'set-readonly'][pd['readonly'] == 'true'])
    return web.json_response({'acknowledged': True})


async def dev_cluster_state(request):
    cluster = request.app['cluster']
    return web.json_response(cluster.state())


def _start(config):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [{name}] %(message)s'.format(name=config['node']['name'])
    )

    logging.info('config: ' + json.dumps(config, indent=2))

    app = web.Application()
    app.add_routes([
        web.get('/api/v1/status', cluster_status),
        web.get('/api/v1/dev/cs', dev_cluster_state),
        web.post('/api/v1/dev/readonly', dev_readonly),
        web.get('/api/v1/logs', list_logs),
        web.get('/api/v1/nodes', list_nodes),
        web.post('/api/v1/log/{log_id}', create),
        web.post('/api/v1/log/{log_id}/replicate', replicate_log),
        web.get('/api/v1/log/{log_id}/status', log_status),
        web.get('/api/v1/log/{log_id}/query', query)
    ])

    local_logs = LocalLogs(config['data_dir'])
    cluster = Cluster(config, config['network']['bind'], config['network']['peers'])
    cluster.set_local_logs(local_logs)
    cluster.start()
    app['config'] = config
    app['cluster'] = cluster
    app['data_dir'] = pathlib.Path(config['data_dir'])
    app['local_logs'] = local_logs

    host = config['network']['bind']
    app['self_addr'] = host

    aiohttp_autoreload.start()
    web.run_app(app, host=host, port=config['network']['app_port'])


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
