import time
import numpy as np
from detector import AnomalyDetector, AnomalyResult
from alert_manager import AlertManager

if __name__ == "__main__":
    detector = AnomalyDetector()
    alert_mgr = AlertManager(limit_per_minute=2, window_seconds=5)  # 限流 2 条/分钟，去重 5 秒

    metric = "cpu"

    # 1️⃣ 填充历史正常数据
    for i in range(30):
        detector.add(metric, np.random.normal(30, 5))

    # 2️⃣ 添加一个异常点
    result = detector.detect(metric, 90)  # 明显异常
    print("Anomaly:", result.to_dict())
    triggered = alert_mgr.add_alert(metric, result)
    print("Triggered?", triggered)

    # 3️⃣ 去重测试：立刻再添加相同异常
    time.sleep(2)
    result2 = detector.detect(metric, 95)
    triggered = alert_mgr.add_alert(metric, result2)
    print("Triggered after 2s (should be False due to dedup)?", triggered)

    # 4️⃣ 去重过期测试：等待去重窗口过期
    time.sleep(5)
    result3 = detector.detect(metric, 100)
    triggered = alert_mgr.add_alert(metric, result3)
    print("Triggered after 7s (should be True)?", triggered)

    # 5️⃣ 限流测试：超过每分钟限制
    result4 = detector.detect(metric, 110)
    triggered = alert_mgr.add_alert(metric, result4)
    print("Triggered 1st limit test?", triggered)
    result5 = detector.detect(metric, 115)
    triggered = alert_mgr.add_alert(metric, result5)
    print("Triggered 2nd limit test (should be False due to rate limit)?", triggered)

    # 6️⃣ 查看当前所有告警
    print("\nAll alerts in cache:")
    for alert in alert_mgr.get_alerts():
        print(alert)
