import logging
import threading
import time
from typing import Dict, List, Tuple

from app.models.anomaly import AnomalyResult

logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, limit_per_minute: int = 5, window_seconds: int = 300):
        self.limit_per_minute = limit_per_minute
        self.window_seconds = window_seconds
        self.alerts_cache: Dict[str, List[Tuple[float, float]]] = {}
        self._lock = threading.Lock()

    def add_alert(self, metric: str, result: AnomalyResult) -> bool:
        if not result.is_anomaly:
            return False

        now = time.time()

        with self._lock:
            if metric not in self.alerts_cache:
                self.alerts_cache[metric] = []

            # Prune expired entries FIRST — this is the memory-leak fix.
            # Before: a temporary filtered list was created for the dedup
            # check, but the backing list was never cleaned, growing without
            # bound.  Now we rewrite the list in-place on every call so its
            # size is bounded by (window_seconds × max alert arrival rate).
            cutoff = now - self.window_seconds
            entries = self.alerts_cache[metric]
            self.alerts_cache[metric] = [
                (t, z) for t, z in entries if t > cutoff
            ]

            if self.alerts_cache[metric]:
                return False

            one_minute_ago = now - 60
            recent_count = sum(
                1 for t, _ in self.alerts_cache[metric] if t > one_minute_ago
            )
            if recent_count >= self.limit_per_minute:
                return False

            self.alerts_cache[metric].append((now, result.z_score))

        logger.debug(
            "Alert accepted — metric=%s z_score=%.2f cache_size=%d",
            metric, result.z_score, len(self.alerts_cache[metric]),
        )
        return True

    def get_alerts(self) -> List[Dict]:
        with self._lock:
            alerts = []
            for metric, entries in self.alerts_cache.items():
                for timestamp, z_score in entries:
                    alerts.append({
                        "metric": metric,
                        "timestamp": timestamp,
                        "z_score": z_score,
                    })
            return alerts
