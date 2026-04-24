import time
import numpy as np

from app.detectors.zscore import AnomalyDetector
from app.services.alerting import AlertManager

if __name__ == "__main__":
    detector = AnomalyDetector()
    alert_mgr = AlertManager(limit_per_minute=2, window_seconds=5)

    metric = "cpu"

    for _ in range(30):
        detector.add(metric, float(np.random.normal(30, 5)))

    result = detector.detect(metric, 90)
    print("Anomaly:", result.to_dict())
    triggered = alert_mgr.add_alert(metric, result)
    print("Triggered?", triggered)

    time.sleep(2)
    result2 = detector.detect(metric, 95)
    triggered = alert_mgr.add_alert(metric, result2)
    print("Triggered after 2s (should be False due to dedup)?", triggered)

    time.sleep(5)
    result3 = detector.detect(metric, 100)
    triggered = alert_mgr.add_alert(metric, result3)
    print("Triggered after 7s (should be True)?", triggered)

    result4 = detector.detect(metric, 110)
    triggered = alert_mgr.add_alert(metric, result4)
    print("Triggered 1st limit test?", triggered)
    result5 = detector.detect(metric, 115)
    triggered = alert_mgr.add_alert(metric, result5)
    print("Triggered 2nd limit test (should be False due to rate limit)?", triggered)

    print("\nAll alerts in cache:")
    for alert in alert_mgr.get_alerts():
        print(alert)
