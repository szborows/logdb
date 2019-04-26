from pysyncobj import SyncObjConsumer, replicated


class Logs(SyncObjConsumer):
    def __init__(self):
        self._logs = {}

    @replicated
    def add_log(self, log_id, log_info):
        if log_id in self._logs:
            raise RuntimeError(f'{log_id} already exists!')
        self._logs[log_id] = log_info

    def get_logs(self):
        return self._logs

    def get_log(self, log_id):
        return self._logs.get(log_id)
