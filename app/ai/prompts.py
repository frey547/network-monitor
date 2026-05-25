from app.models.alert import AlertInput, RuleResult

SYSTEM_PROMPT = (
    "你是SRE告警增强分析助手。补充规则引擎的分析结果。\n"
    "要求：仅返回JSON，不要markdown，不要代码块，每个字段20字以内。"
)

RESPONSE_SCHEMA = '{"summary":"…","risk_analysis":"…","additional_suggestions":["…"]}'


def build_enhancement_prompt(alert: AlertInput, rule_result: RuleResult) -> str:
    return (
        f"告警: {alert.alertname}\n"
        f"实例: {alert.instance}\n"
        f"值: {alert.value}\n"
        f"规则判定: {rule_result.reason}\n\n"
        f"请补充JSON：{RESPONSE_SCHEMA}"
    )


def build_unknown_alert_prompt(alert: AlertInput) -> str:
    labels_brief = str(alert.labels)[:200]
    return (
        f"未知告警:\n"
        f"名称: {alert.alertname}\n"
        f"实例: {alert.instance}\n"
        f"值: {alert.value}\n"
        f"描述: {alert.description}\n"
        f"标签: {labels_brief}\n\n"
        f"请返回JSON：{RESPONSE_SCHEMA}"
    )
