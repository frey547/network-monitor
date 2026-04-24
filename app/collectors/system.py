import time
from typing import Dict

import psutil


class SystemCollector:
    def __init__(self):
        self._last_timestamp = None
        self._last_bytes_sent = None
        self._last_bytes_recv = None

    def collect(self) -> Dict[str, float]:
        now = time.time()
        network = psutil.net_io_counters()

        bytes_sent_per_sec = 0.0
        bytes_recv_per_sec = 0.0

        if self._last_timestamp is not None:
            elapsed = now - self._last_timestamp
            if elapsed > 0:
                bytes_sent_per_sec = (network.bytes_sent - self._last_bytes_sent) / elapsed
                bytes_recv_per_sec = (network.bytes_recv - self._last_bytes_recv) / elapsed

        self._last_timestamp = now
        self._last_bytes_sent = network.bytes_sent
        self._last_bytes_recv = network.bytes_recv

        return {
            "cpu": float(psutil.cpu_percent(interval=None)),
            "memory": float(psutil.virtual_memory().percent),
            "disk": float(psutil.disk_usage("/").percent),
            "network_sent": float(bytes_sent_per_sec),
            "network_recv": float(bytes_recv_per_sec),
        }
