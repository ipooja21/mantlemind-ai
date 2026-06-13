import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [Telegram] %(message)s")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def send_telegram_alert(message: str, parse_mode: str = "Markdown") -> bool:
    
    if not BOT_TOKEN or not CHAT_ID:
        logging.warning("Telegram not configured — skipping alert")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            logging.info("Telegram alert sent ✓")
            return True
        else:
            logging.warning("Telegram %d: %s", resp.status_code, resp.text[:150])
            return False
    except Exception as e:
        logging.error("Telegram error: %s", e)
        return False


def format_whale_alert(address: str, value_mnt: float, pattern: str, score: float) -> str:
    return (
        f"🐋 *WHALE ALERT — MantleMind AI*\n"
        f"Address: `{address}`\n"
        f"Pattern: *{pattern}*\n"
        f"Volume: {value_mnt:,.0f} MNT\n"
        f"Score: {score:.2f}/100\n"
        f"_Mantle Network · Real-time on-chain intelligence_"
    )


def format_anomaly_alert(anomaly_rate: float, critical_txs: int, total_detected: int) -> str:
    return (
        f"⚠️ *ANOMALY ALERT — MantleMind AI*\n"
        f"Anomaly Rate: {anomaly_rate:.1f}%\n"
        f"Critical Transactions: {critical_txs}\n"
        f"Total Detected: {total_detected}\n"
        f"_Mantle Network · Real-time on-chain intelligence_"
    )


def format_cluster_alert(cluster_id: str, wallet_count: int, label: str, confidence: int) -> str:
    return (
        f"🕸️ *WALLET CLUSTER DETECTED — MantleMind AI*\n"
        f"Cluster: `{cluster_id}`\n"
        f"Wallets linked: {wallet_count}\n"
        f"Pattern: *{label}*\n"
        f"Confidence: {confidence}%\n"
        f"_Mantle Network · Smart money tracking_"
    )


def format_alpha_signal(alpha_score: float, signal: str, insight: str) -> str:
    return (
        f"📊 *ALPHA SIGNAL — MantleMind AI*\n"
        f"Score: {alpha_score:.1f}/100\n"
        f"Signal: *{signal}*\n\n"
        f"{insight}\n\n"
        f"_Mantle Network · AI-powered analysis_"
    )


if __name__ == "__main__":
    
    ok = send_telegram_alert("✅ MantleMind AI Telegram bot is connected and working!")
    print("Sent:", ok)