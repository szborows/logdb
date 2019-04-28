import logging
import queue
import datetime
import random
import os
import requests
from datetime import datetime


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')


def _free_disk_space(cluster):
    stat = os.statvfs(cluster.config['data_dir'])
    return stat.f_bfree * stat.f_bsize


def node_worker(cluster, self_addr, initial_role, q):
    role = initial_role
    readonly = False

    def common_work():
        cluster.nodes.update_node(self_addr, {'readonly': readonly, 'disk_space': _free_disk_space(cluster)})

    def leader_work():

        def should_replicate_log(log_info):
            if len(log_info['replicas']) == 2:
                return False
            # TODO: replicating can take forever! should check some dates too..
            if 'replicating' in log_info and  log_info['replicating']:
                return False
            return True

        logging.info('leader active')
        logs = cluster.logs.get_logs()
        for log_id in logs:
            log_info = logs[log_id]
            if should_replicate_log(log_info):
                logging.info(f'log {log_id} should be replicated. {log_info}')
                possible_replica_nodes = [k for k, v in cluster.nodes.get_nodes().items() if k != log_info['replicas'][0] and not v['readonly']]

                if not possible_replica_nodes:
                    # perhaps Raft sync is still in progress?
                    # if so, we should never fire {leader,follower}_work() function...
                    continue

                origin_node = log_info['replicas'][0]
                target_node = random.choice(possible_replica_nodes)
                logging.info(f'possible nodes for replication: {possible_replica_nodes}. picked {target_node}')
                # data races. data races everywhere...
                try:
                    app_port = cluster.config['network']['app_port']
                    r = requests.post(f'http://{origin_node}:{app_port}/api/v1/log/{log_id}/replicate', {'target_node': target_node})
                    r.raise_for_status()
                    cluster.logs.update_log(log_id, {'replicating': True, 'replication_started_at': _now(), 'replication_origin': origin_node, 'replication_target': target_node})
                    logging.info(f'Requested log replication for log {log_id}: {origin_node} -> {target_node}')
                except requests.exceptions.ConnectionError:
                    logging.exception(f'Failed to order replication, {origin_node} -> {target_node}')

    def follower_work():
        logging.debug('doing follower work')

    while True:
        try:
            item = q.get(timeout=1)
            if item is None:
                break
            if item == 'leader':
                role = 'leader'
            elif item == 'follower':
                role = 'follower'
            elif item == 'set-readonly':
                readonly = True
            elif item == 'set-readwrite':
                readonly = False
            q.task_done()
        except queue.Empty:
            try:
                common_work()
                if role == 'leader':
                    leader_work()
                else:
                    follower_work()
            except Exception:
                logging.exception('Encountered exception in worker thread')
