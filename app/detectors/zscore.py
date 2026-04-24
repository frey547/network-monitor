from typing import Dict, List

import numpy as np

from app.detectors.detector import Detector
from app.models.anomaly import Anomaly


class AnomalyDetector(Detector):
    def __init__(self, window_size: int = 50, threshold: float = 3.0):
        self.window_size = window_size
        self.threshold = threshold
        self.data: Dict[str, List[float]] = {}

    def add(self, metric: str, value: float) -> None:
        if metric not in self.data:
            self.data[metric] = []

        self.data[metric].append(value)

        if len(self.data[metric]) > self.window_size:
            self.data[metric].pop(0)

    def detect(self, metric: str, value: float, timestamp: float) -> Anomaly:
        values = self.data.get(metric, [])

        if len(values) < 10:
            return Anomaly(
                timestamp=timestamp,
                metric=metric,
                value=value,
                is_anomaly=False,
                score=0.0,
                baseline=0.0
            )

        mean = float(np.mean(values))
        std = float(np.std(values))

        if std == 0:
            return Anomaly(
                timestamp=timestamp,
                metric=metric,
                value=value,
                is_anomaly=False,
                score=0.0,
                baseline=mean
            )

        z_score = (value - mean) / std
        is_anomaly = abs(z_score) > self.threshold

        return Anomaly(
            timestamp=timestamp,
            metric=metric,
            value=value,
            is_anomaly=is_anomaly,
            score=z_score,
            baseline=mean
        )
