import os

from dotenv import load_dotenv

load_dotenv()

# ---------- AI API ----------
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY") or os.getenv("LINO_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://linoapi.com.cn/v1")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ---------- AI behavior ----------
AI_ENABLED: bool = os.getenv("AI_ENABLED", "true").lower() == "true"
AI_MAX_TOKENS: int = int(os.getenv("AI_MAX_TOKENS", "200"))
AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.1"))

# ---------- Feishu ----------
FEISHU_WEBHOOK_URL: str = os.getenv("FEISHU_WEBHOOK_URL", "")
