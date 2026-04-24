import threading
import time
import uuid
from typing import Optional

from app.collectors.simulated import SimulatedCollector
from app.collectors.system import SystemCollector
from app.detectors.threshold import ThresholdDetector
from app.detectors.zscore import AnomalyDetector
from app.models.anomaly import Anomaly
from app.models.event import Event
from app.models.metric import Metric
from app.services.alerting import AlertManager
from app.storage.repository import Repository


class SimulationService:
    def __init__(
        self,
        repository: Repository,
        detector: AnomalyDetector,
        alert_manager: AlertManager,
        interval_seconds: int = 2,
        collector_type: str = "simulated",
    ):
        self.repository = repository
        self.detectors = {
            "zscore": detector,
            "threshold": ThresholdDetector(80),
        }
        self.detector_config = {
            "cpu": ["zscore", "threshold"],
            "memory": ["zscore"],
        }
        self.alert_manager = alert_manager
        self.interval_seconds = interval_seconds
        self.collector = self._build_collector(collector_type)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _build_collector(self, collector_type: str):
        if collector_type == "system":
            return SystemCollector()
        return SimulatedCollector()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            metrics = self.collector.collect()
            timestamp = time.time()

            for metric_name, value in metrics.items():
                metric = Metric(timestamp=timestamp, name=metric_name, value=value, labels={})
                self.repository.add_metric(metric)

                detector_names = self.detector_config.get(metric_name, list(self.detectors.keys()))
                active_detectors = {
                    name: self.detectors[name]
                    for name in detector_names
                    if name in self.detectors
                }
                if not active_detectors:
                    active_detectors = self.detectors

                for detector in active_detectors.values():
                    detector.add(metric_name, value)

                first_result = None
                raw = None
                for name, detector in active_detectors.items():
                    result = detector.detect(metric_name, value, timestamp)
                    if first_result is None:
                        first_result = result
                    if result.is_anomaly and (raw is None or name == "threshold"):
                        raw = result

                if raw is None:
                    raw = first_result
                anomaly = Anomaly(
                    timestamp=timestamp,
                    metric=metric_name,
                    value=value,
                    is_anomaly=raw.is_anomaly,
                    score=raw.score,
                    baseline=raw.baseline,
                )
                self.repository.add_anomaly(anomaly)

                if anomaly.is_anomaly:
                    triggered = self.alert_manager.add_alert(metric_name, anomaly)
                    if triggered:
                        event = Event(
                            event_id=str(uuid.uuid4()),
                            metric=metric_name,
                            source="localhost",
                            severity="warning",
                            status="open",
                            timestamp=timestamp,
                        )
                        self.repository.add_event(event)
                        print(f"[ALERT] {metric_name} abnormal! z={anomaly.score:.2f}")

            self._stop_event.wait(self.interval_seconds)
