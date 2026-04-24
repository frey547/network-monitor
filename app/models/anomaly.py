from dataclasses import asdict, dataclass


@dataclass
class Anomaly:
    timestamp: float
    metric: str
    value: float
    is_anomaly: bool
    score: float
    baseline: float

    @property
    def z_score(self) -> float:
        return self.score

    @property
    def mean(self) -> float:
        return self.baseline

    def to_dict(self):
        return asdict(self)


AnomalyResult = Anomaly
