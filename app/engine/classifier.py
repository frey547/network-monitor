from app.engine.rules import ALERT_RULES
from app.models.alert import AlertType


def classify_alert(alertname: str, labels: dict | None = None) -> AlertType:
    normalized = alertname.lower().replace("_", "").replace("-", "").replace(" ", "")

    for type_key, rule in ALERT_RULES.items():
        for pattern in rule["patterns"]:
            if pattern in normalized:
                return AlertType(type_key)

    if labels:
        label_str = " ".join(str(v) for v in labels.values()).lower()
        for type_key, rule in ALERT_RULES.items():
            for pattern in rule["patterns"]:
                if pattern in label_str:
                    return AlertType(type_key)

    return AlertType.UNKNOWN
