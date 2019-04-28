from pysyncobj import SyncObj, SyncObjConf
from pysyncobj.batteries import ReplDict
import threading
import queue
import logging
import copy

from nodes import Nodes
from logs import Logs, LogState
from node_worker import node_worker
from utils import RaftState


class Cluster:
    def __init__(self, config, addr, peers):
        self._addr = addr
        self._peers = peers
        self.logs = Logs()
        self._raft_port = config['network']['raft_port']

    def set_local_logs(self, local_logs):
        self._local_logs = local_logs

    def start(self):
        logging.info('Start')

        self.nodes = Nodes()
        self.worker_q = queue.Queue()
        self.worker = threading.Thread(target=node_worker, args=(self, self._addr, 'slave', self.worker_q))
        self.worker.daemon = True

        self._syncObjConf = SyncObjConf(
            onReady=lambda: self._onReady(),
            onStateChanged=lambda os, ns: self._stateChanged(os, ns)
        )
        self._syncObj = SyncObj(
            f'{self._addr}:{self._raft_port}',
            [f'{p}:{self._raft_port}' for p in self._peers],
            consumers=[self.logs, self.nodes],
            conf=self._syncObjConf
        )

    def local_msg(self, msg):
        self.worker_q.put(msg)

    def _onReady(self):
        logging.info(f'Raft ready...')
        self.worker.start()
        self.sync_logs()

    def sync_logs(self):
        if self._local_logs.logs:
            logging.info('sending info about local logs')
        # it still doesn't support log replicas...
        for log in self._local_logs.logs:
            if log in self.logs.get_logs():
                continue
            logging.warning(log)
            self.logs.add_log(log, {'replicas': [self._addr], 'state': LogState.SHOULD_REPLICATE})

    def _stateChanged(self, oldState, newState):
        if newState == RaftState.LEADER:
            self.worker_q.put('leader')
            state = 'leader'
        elif newState == RaftState.FOLLOWER:
            self.worker_q.put('follower')
            state = 'follower'
        else:
            state = 'candidate'

        logging.info(f'changed Raft role to: {state}')

    def state(self):
        return {
            'logs': copy.copy(self.logs.get_logs()),
            'nodes': copy.copy(self.nodes.get_nodes())
        }

    def healthy(self):
        return self._syncObj.getStatus()['leader'] is not None

