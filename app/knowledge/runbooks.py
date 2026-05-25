from app.engine.rules import ALERT_RULES
from app.models.alert import AlertType


def get_runbook(alert_type: AlertType) -> str:
    rule = ALERT_RULES.get(alert_type.value)
    if rule:
        return rule["runbook"]
    return "未找到对应的排查手册"
