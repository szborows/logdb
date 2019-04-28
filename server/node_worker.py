import logging
import queue
import datetime
import random


def node_worker(cluster, self_addr, initial_role, q):
    role = initial_role
    readonly = False

    def common_work():
        cluster.nodes.update_node(self_addr, {'readonly': readonly, 'disk_space': 0})
        # report disk usage
        pass

    def leader_work():
        logging.info('doing leader work')
        logs = cluster.logs.get_logs()
        for log_id in logs:
            log_info = logs[log_id]
            if len(log_info['replicas']) < 2:
                logging.info(f'log {log_id} should be replicated. {log_info}')
                possible_replica_nodes = [k for k, v in cluster.nodes.get_nodes().items() if k != log_info['replicas'][0] and not v['readonly']]

                if not possible_replica_nodes:
                    # perhaps Raft sync is still in progress?
                    # if so, we should never fire {leader,follower}_work() function...
                    continue
                logging.info(f'possible nodes for replication: {possible_replica_nodes}')
                replica_node = random.choice(possible_replica_nodes)
                logging.info(f'picked {replica_node} replication node')

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
            common_work()
            if role == 'leader':
                leader_work()
            else:
                follower_work()

