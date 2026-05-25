import logging
import os

import httpx

from app.models.alert import AnalysisResult, Severity

logger = logging.getLogger(__name__)

_SEVERITY_COLOR = {
    Severity.CRITICAL: "red",
    Severity.WARNING: "orange",
    Severity.INFO: "green",
}

_SEVERITY_ICON = {
    Severity.CRITICAL: "[P0 CRITICAL]",
    Severity.WARNING: "[P1 WARNING]",
    Severity.INFO: "[P2 INFO]",
}


class FeishuNotifier:
    def __init__(self, webhook_url: str = "") -> None:
        self.webhook_url = webhook_url or os.getenv("FEISHU_WEBHOOK_URL", "")
        if self.webhook_url:
            redacted = self.webhook_url[:40] + "***"
            logger.info("FeishuNotifier initialised, webhook_url=%s", redacted)
        else:
            logger.warning(
                "FeishuNotifier initialised WITHOUT webhook URL — "
                "set FEISHU_WEBHOOK_URL in env or .env"
            )

    async def send(
        self,
        result: AnalysisResult,
        alert_name: str = "",
        instance: str = "",
    ) -> bool:
        if not self.webhook_url:
            logger.warning("Feishu send skipped: webhook URL is empty")
            return False

        card = self._build_card(result, alert_name, instance)

        logger.info(
            "Feishu send starting — alert_name=%s instance=%s severity=%s",
            alert_name, instance, result.severity.value,
        )

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.webhook_url, json=card, timeout=10,
                )
        except Exception:
            logger.exception("Feishu send failed — network/timeout error")
            return False

        body_text = resp.text
        status_code = resp.status_code

        if status_code != 200:
            logger.error(
                "Feishu returned HTTP %d — body=%s", status_code, body_text,
            )
            return False

        try:
            body = resp.json()
        except Exception:
            logger.error(
                "Feishu returned non-JSON response — status=%d body=%s",
                status_code, body_text,
            )
            return False

        feishu_code = body.get("code")
        feishu_msg = body.get("msg", "")

        if feishu_code != 0:
            logger.error(
                "Feishu rejected message — code=%s msg=%s body=%s",
                feishu_code, feishu_msg, body_text,
            )
            return False

        logger.info(
            "Feishu send succeeded — alert_name=%s instance=%s",
            alert_name, instance,
        )
        return True

    def _build_card(
        self,
        result: AnalysisResult,
        alert_name: str,
        instance: str,
    ) -> dict:
        icon = _SEVERITY_ICON.get(result.severity, "[ALERT]")
        color = _SEVERITY_COLOR.get(result.severity, "grey")
        title = f"{icon} {alert_name or result.alert_type.value}"

        elements: list[dict] = []

        fields = []
        if alert_name:
            fields.append(self._field("告警名称", alert_name))
        if instance:
            fields.append(self._field("实例", instance))
        fields.append(self._field("类型", result.alert_type.value))
        fields.append(self._field("级别", result.severity.value))
        elements.append({"tag": "div", "fields": fields})
        elements.append({"tag": "hr"})

        elements.append(self._md_block("原因分析", result.reason))

        suggestion_text = "\n".join(f"• {s}" for s in result.suggestions)
        elements.append(self._md_block("处理建议", suggestion_text))

        if result.commands:
            cmd_text = "\n".join(f"`{c}`" for c in result.commands[:4])
            elements.append(self._md_block("排查命令", cmd_text))

        if result.ai_summary:
            elements.append({"tag": "hr"})
            ai_text = result.ai_summary
            if result.ai_suggestions:
                ai_text += "\n" + "\n".join(f"• {s}" for s in result.ai_suggestions)
            elements.append(self._md_block("AI 补充分析", ai_text))

        elements.append(
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"分析来源: {result.source} | AIOps Monitor",
                    }
                ],
            }
        )

        return {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": color,
                },
                "elements": elements,
            },
        }

    @staticmethod
    def _field(label: str, value: str) -> dict:
        return {
            "is_short": True,
            "text": {"tag": "lark_md", "content": f"**{label}**\n{value}"},
        }

    @staticmethod
    def _md_block(title: str, body: str) -> dict:
        return {
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**{title}**\n{body}"},
        }
