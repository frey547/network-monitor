from app.models.anomaly import Anomaly
from app.detectors.detector import Detector


class ThresholdDetector(Detector):
    def __init__(self, threshold: float = 80):
        self.threshold = threshold

    def add(self, metric: str, value: float) -> None:
        pass

    def detect(self, metric: str, value: float, timestamp: float) -> Anomaly:
        return Anomaly(
            timestamp=timestamp,
            metric=metric,
            value=value,
            is_anomaly=value > self.threshold,
            score=value,
            baseline=self.threshold,
        )
