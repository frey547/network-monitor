import time
from typing import Dict, List, Tuple
from detector import AnomalyResult

class AlertManager:
    def __init__(self, limit_per_minute: int = 5, window_seconds: int = 300):
        self.limit_per_minute = limit_per_minute
        self.window_seconds = window_seconds
        self.alerts_cache: Dict[str, List[Tuple[float, float]]] = {}  # metric -> [(timestamp, z_score)]

    def add_alert(self, metric: str, result: AnomalyResult) -> bool:
        """添加异常结果，返回是否触发告警"""
        if not result.is_anomaly:
            return False

        now = time.time()
        if metric not in self.alerts_cache:
            self.alerts_cache[metric] = []

        # 去重：同 metric 最近告警时间 < window_seconds 不触发
        recent_alerts = [t for t, _ in self.alerts_cache[metric] if now - t < self.window_seconds]
        if recent_alerts:
            return False

        # 限流：统计最近一分钟已触发告警数
        one_minute_ago = now - 60
        recent_count = sum(1 for t, _ in self.alerts_cache[metric] if t > one_minute_ago)
        if recent_count >= self.limit_per_minute:
            return False

        # 触发告警
        self.alerts_cache[metric].append((now, result.z_score))
        return True

    def get_alerts(self) -> List[Dict]:
        """返回当前缓存的告警信息"""
        alerts = []
        for metric, entries in self.alerts_cache.items():
            for timestamp, z_score in entries:
                alerts.append({
                    "metric": metric,
                    "timestamp": timestamp,
                    "z_score": z_score
                })
        return alerts
