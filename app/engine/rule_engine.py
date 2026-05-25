from app.engine.classifier import classify_alert
from app.engine.rules import ALERT_RULES
from app.models.alert import AlertInput, AlertType, RuleResult, Severity


class RuleEngine:
    def evaluate(self, alert: AlertInput) -> RuleResult:
        alert_type = classify_alert(alert.alertname, alert.labels)

        if alert_type == AlertType.UNKNOWN:
            return self._unknown_result(alert)

        rule = ALERT_RULES[alert_type.value]
        severity = self._determine_severity(alert.value, rule["severity_thresholds"])

        return RuleResult(
            alert_type=alert_type,
            severity=severity,
            reason=rule["reason"],
            suggestions=rule["suggestions"],
            commands=rule["commands"],
            runbook=rule["runbook"],
            matched_rule=alert_type.value,
        )

    @staticmethod
    def _determine_severity(
        value: float | None,
        thresholds: dict[str, float],
    ) -> Severity:
        if value is None:
            return Severity.WARNING

        if value >= thresholds.get("critical", float("inf")):
            return Severity.CRITICAL
        if value >= thresholds.get("warning", float("inf")):
            return Severity.WARNING
        return Severity.INFO

    @staticmethod
    def _unknown_result(alert: AlertInput) -> RuleResult:
        return RuleResult(
            alert_type=AlertType.UNKNOWN,
            severity=Severity.WARNING,
            reason=f"未匹配规则的告警: {alert.alertname}",
            suggestions=[
                "请检查告警详情并人工分析",
                "考虑为该告警类型添加规则",
            ],
            commands=[
                "dmesg | tail -30",
                "journalctl -xe --no-pager | tail -30",
            ],
            runbook="未知告警类型，请人工排查",
            matched_rule="",
        )
