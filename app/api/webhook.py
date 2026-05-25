import logging

from fastapi import APIRouter, Request

from app.models.alert import AlertInput

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhook"])


def _parse_alertmanager_alert(raw: dict) -> AlertInput:
    labels = raw.get("labels", {})
    annotations = raw.get("annotations", {})

    value = None
    for key in ("value", "current_value"):
        raw_val = annotations.get(key) or labels.get(key)
        if raw_val is not None:
            try:
                value = float(str(raw_val).rstrip("%"))
            except (ValueError, TypeError):
                pass
            else:
                break

    return AlertInput(
        alertname=labels.get("alertname", ""),
        status=raw.get("status", "firing"),
        instance=labels.get("instance", ""),
        description=annotations.get("description", ""),
        value=value,
        labels=labels,
        annotations=annotations,
    )


@router.post("/webhook/alert")
async def webhook_alert(request: Request):
    data = await request.json()
    alerts = data.get("alerts", [])

    if not alerts:
        return {"status": "ok", "message": "no alerts"}

    rule_engine = request.app.state.rule_engine
    ai_analyzer = request.app.state.ai_analyzer
    enricher = request.app.state.enricher
    feishu = request.app.state.feishu

    results = []
    notify_ok = 0
    notify_fail = 0

    for raw_alert in alerts:
        alert = _parse_alertmanager_alert(raw_alert)
        logger.info("Processing alert: %s instance=%s", alert.alertname, alert.instance)

        rule_result = rule_engine.evaluate(alert)

        ai_result = None
        if ai_analyzer.should_enhance(rule_result):
            ai_result = ai_analyzer.enhance(alert, rule_result)

        analysis = enricher.enrich(alert, rule_result, ai_result)

        sent = await feishu.send(analysis, alert_name=alert.alertname, instance=alert.instance)
        if sent:
            notify_ok += 1
        else:
            notify_fail += 1
            logger.error(
                "Feishu notification FAILED for alert=%s instance=%s",
                alert.alertname, alert.instance,
            )

        results.append(analysis.model_dump())

    logger.info(
        "Webhook batch done — total=%d notify_ok=%d notify_fail=%d",
        len(results), notify_ok, notify_fail,
    )

    return {
        "status": "ok" if notify_fail == 0 else "partial",
        "count": len(results),
        "notify_ok": notify_ok,
        "notify_fail": notify_fail,
        "results": results,
    }
