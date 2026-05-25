import time
from dataclasses import dataclass

from app.models.alert import AlertInput


@dataclass
class AlertRecord:
    alertname: str
    instance: str
    timestamp: float


class AlertHistory:
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._records: list[AlertRecord] = []

    def record(self, alert: AlertInput) -> None:
        self._records.append(
            AlertRecord(
                alertname=alert.alertname,
                instance=alert.instance,
                timestamp=time.time(),
            )
        )
        if len(self._records) > self.max_size:
            self._records = self._records[-self.max_size :]

    def recent_count(self, alertname: str, window_minutes: int = 30) -> int:
        cutoff = time.time() - window_minutes * 60
        return sum(
            1
            for r in self._records
            if r.alertname == alertname and r.timestamp > cutoff
        )

    def get_recent(self, alertname: str, limit: int = 10) -> list[AlertRecord]:
        matches = [r for r in self._records if r.alertname == alertname]
        return matches[-limit:]
