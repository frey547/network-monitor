import time
from typing import Dict, List, Tuple

from app.models.anomaly import AnomalyResult


class AlertManager:
    def __init__(self, limit_per_minute: int = 5, window_seconds: int = 300):
        self.limit_per_minute = limit_per_minute
        self.window_seconds = window_seconds
        self.alerts_cache: Dict[str, List[Tuple[float, float]]] = {}

    def add_alert(self, metric: str, result: AnomalyResult) -> bool:
        if not result.is_anomaly:
            return False

        now = time.time()
        if metric not in self.alerts_cache:
            self.alerts_cache[metric] = []

        recent_alerts = [t for t, _ in self.alerts_cache[metric] if now - t < self.window_seconds]
        if recent_alerts:
            return False

        one_minute_ago = now - 60
        recent_count = sum(1 for t, _ in self.alerts_cache[metric] if t > one_minute_ago)
        if recent_count >= self.limit_per_minute:
            return False

        self.alerts_cache[metric].append((now, result.z_score))
        return True

    def get_alerts(self) -> List[Dict]:
        alerts = []
        for metric, entries in self.alerts_cache.items():
            for timestamp, z_score in entries:
                alerts.append({
                    "metric": metric,
                    "timestamp": timestamp,
                    "z_score": z_score,
                })
        return alerts
