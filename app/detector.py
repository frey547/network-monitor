from typing import Dict, List, Tuple
import numpy as np


class AnomalyResult:
    def __init__(self, is_anomaly: bool, z_score: float, mean: float, std: float):
        self.is_anomaly = is_anomaly
        self.z_score = z_score
        self.mean = mean
        self.std = std

    def to_dict(self):
        return {
            "is_anomaly": self.is_anomaly,
            "z_score": self.z_score,
            "mean": self.mean,
            "std": self.std,
        }


class AnomalyDetector:
    def __init__(self, window_size: int = 50, threshold: float = 3.0):
        self.window_size = window_size
        self.threshold = threshold
        self.data: Dict[str, List[float]] = {}

    def add(self, metric: str, value: float) -> None:
        """添加数据点"""
        if metric not in self.data:
            self.data[metric] = []

        self.data[metric].append(value)

        # 控制窗口大小
        if len(self.data[metric]) > self.window_size:
            self.data[metric].pop(0)

    def detect(self, metric: str, value: float) -> AnomalyResult:
        """检测是否异常"""
        values = self.data.get(metric, [])

        # 冷启动保护
        if len(values) < 10:
            return AnomalyResult(False, 0.0, 0.0, 0.0)

        mean = float(np.mean(values))
        std = float(np.std(values))

        # 防止除零
        if std == 0:
            return AnomalyResult(False, 0.0, mean, std)

        z_score = (value - mean) / std
        is_anomaly = abs(z_score) > self.threshold

        return AnomalyResult(is_anomaly, z_score, mean, std)
