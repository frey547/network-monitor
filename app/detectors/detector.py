from abc import ABC, abstractmethod

from app.models.anomaly import Anomaly


class Detector(ABC):
    @abstractmethod
    def add(self, metric: str, value: float) -> None:
        pass

    @abstractmethod
    def detect(self, metric: str, value: float, timestamp: float) -> Anomaly:
        pass
