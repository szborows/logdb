from pysyncobj import SyncObjConsumer, replicated


class Nodes(SyncObjConsumer):
    def __init__(self):
        self._nodes = {}

    @replicated
    def update_node(self, node_addr, node_info):
        if node_addr not in self._nodes:
            self._nodes[node_addr] = node_info
        self._nodes[node_addr].update(node_info)

    def get_nodes(self):
        return self._nodes
