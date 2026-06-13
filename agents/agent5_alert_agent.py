import json
import time
import asyncio
import hashlib
import os
from typing import Optional
from loguru import logger

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    WHALE_THRESHOLD_MNT,
    ALPHA_ALERT_THRESHOLD,
    ANOMALY_ALERT_THRESHOLD,
    ALERT_HISTORY_FILE,
)

try:
    import telegram
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("[AlertAgent] python-telegram-bot not installed — Telegram disabled")


DEDUP_WINDOW_SECONDS = 60
MAX_HISTORY = 500


class AlertAgent:
    def __init__(self):
        self.bot: Optional[object] = None
        self.history: list[dict] = self._load_history()
        self._recent_hashes: dict[str, float] = {}
        self._init_telegram()
        logger.success("[AlertAgent] Initialised")

    def _init_telegram(self):
        if not TELEGRAM_AVAILABLE:
            return
        if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
            logger.info("[AlertAgent] Telegram token not configured — alert logging only")
            return
        try:
            self.bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
            logger.success("[AlertAgent] Telegram bot initialised")
        except Exception as e:
            logger.warning(f"[AlertAgent] Telegram init failed: {e}")

    def send_whale_alert(self, whale: dict):
        if whale.get("score", 0) < 40:
            return
        self._dispatch(whale.get("message", "🐋 Whale detected"), alert_type="WHALE", data=whale)

    def send_anomaly_alert(self, summary: dict):
        critical = summary.get("critical_count", 0)
        rate = summary.get("anomaly_rate", 0)
        if critical < 1 and rate < 10:
            return
        msg = (
            f"⚠️ *Anomaly Alert — Mantle Network*\n"
            f"Anomaly Rate: {rate:.1f}%\n"
            f"Critical Transactions: {critical}\n"
            f"Total Detected: {summary.get('total_anomalies', 0)}"
        )
        self._dispatch(msg, alert_type="ANOMALY", data=summary)

    def send_alpha_alert(self, alpha: dict):
        if not alpha.get("is_alert", False):
            return
        score = alpha.get("alpha_score", 0)
        signal = alpha.get("signal", "")
        emoji = alpha.get("emoji", "")
        msg = (
            f"{emoji} *Alpha Signal — {signal}*\n"
            f"Score: {score}/100\n"
            f"Blocks Analysed: {alpha.get('blocks_analysed', 0)}\n"
            f"Transactions: {alpha.get('tx_count', 0)}"
        )
        self._dispatch(msg, alert_type="ALPHA", data=alpha)

    def send_custom(self, message: str, alert_type: str = "INFO"):
        self._dispatch(message, alert_type=alert_type)

    def _dispatch(self, message: str, alert_type: str = "INFO", data: dict = None):
        msg_hash = hashlib.md5(message.encode()).hexdigest()[:12]
        now = time.time()
        if msg_hash in self._recent_hashes:
            if now - self._recent_hashes[msg_hash] < DEDUP_WINDOW_SECONDS:
                logger.debug(f"[AlertAgent] Dedup suppressed: {msg_hash}")
                return
        self._recent_hashes[msg_hash] = now

        record = {
            "id": msg_hash,
            "timestamp": int(now),
            "type": alert_type,
            "message": message,
            "data": data or {},
        }
        self.history.append(record)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]
        self._save_history()

        logger.info(f"[AlertAgent] {alert_type}: {message[:80]}…" if len(message) > 80 else f"[AlertAgent] {alert_type}: {message}")

        
        if self.bot and TELEGRAM_CHAT_ID:
            try:
                asyncio.run(self._async_send(message))
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._async_send(message))
                finally:
                    loop.close()

        
        try:
            from telegram_notifier import send_telegram_alert
            send_telegram_alert(message, alert_type=alert_type)
        except Exception as e:
            logger.warning(f"[AlertAgent] telegram_notifier failed: {e}")

        
        try:
            from discord_notifier import send_discord_alert
            send_discord_alert(message, alert_type=alert_type)
        except Exception as e:
            logger.warning(f"[AlertAgent] discord_notifier failed: {e}")

    async def _async_send(self, message: str):
        try:
            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode="Markdown",
            )
            logger.debug("[AlertAgent] Telegram message sent")
        except Exception as e:
            logger.warning(f"[AlertAgent] Telegram send failed: {e}")

    def _load_history(self) -> list[dict]:
        if os.path.exists(ALERT_HISTORY_FILE):
            try:
                with open(ALERT_HISTORY_FILE, "r") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
            except Exception:
                return []
        return []

    def _save_history(self):
        try:
            with open(ALERT_HISTORY_FILE, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.warning(f"[AlertAgent] History save failed: {e}")

    def get_recent_alerts(self, n: int = 20) -> list[dict]:
        return sorted(self.history[-n:], key=lambda x: x["timestamp"], reverse=True)

    def get_stats(self) -> dict:
        if not self.history:
            return {"total": 0}
        from collections import Counter
        types = Counter(a["type"] for a in self.history)
        return {
            "total": len(self.history),
            "by_type": dict(types),
            "latest_ts": self.history[-1]["timestamp"] if self.history else 0,
        }


if __name__ == "__main__":
    agent = AlertAgent()
    agent.send_custom("🧪 MantleMind test alert — system operational", "TEST")
    print(agent.get_recent_alerts(5))
    print(agent.get_stats())