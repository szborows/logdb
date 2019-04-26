import logging
import queue


def node_worker(cluster, self_addr, initial_role, q):
    role = initial_role

    def common_work():
        cluster.nodes.update_node(self_addr, {'disk_space': 0})
        # report disk usage
        pass

    def leader_work():
        logging.info('doing leader work')
        # iterate through logs. find logs which aren't replicated and order replication

    def follower_work():
        logging.info('doing follower work')

    while True:
        try:
            item = q.get(timeout=1)
            if item is None:
                break
            if item == 'leader':
                role = 'leader'
            elif item == 'follower':
                role = 'follower'
            q.task_done()
        except queue.Empty:
            common_work()
            if role == 'leader':
                leader_work()
            else:
                follower_work()

