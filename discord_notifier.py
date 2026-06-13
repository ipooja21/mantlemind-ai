import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [Discord] %(message)s")

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()


def send_discord_alert(message: str, username: str = "MantleMind AI") -> bool:
    
    if not WEBHOOK_URL:
        logging.warning("Discord webhook not configured — skipping alert")
        return False

    try:
        resp = requests.post(
            WEBHOOK_URL,
            json={"content": message, "username": username},
            timeout=10,
        )
        if resp.status_code in (200, 204):
            logging.info("Discord alert sent ✓")
            return True
        else:
            logging.warning("Discord %d: %s", resp.status_code, resp.text[:150])
            return False
    except Exception as e:
        logging.error("Discord error: %s", e)
        return False


def send_discord_embed(title: str, description: str, color: int = 0x22d3ee,
                        fields: list = None) -> bool:
    
    if not WEBHOOK_URL:
        logging.warning("Discord webhook not configured — skipping alert")
        return False

    embed = {
        "title": title,
        "description": description,
        "color": color,
    }
    if fields:
        embed["fields"] = fields

    try:
        resp = requests.post(
            WEBHOOK_URL,
            json={"username": "MantleMind AI", "embeds": [embed]},
            timeout=10,
        )
        if resp.status_code in (200, 204):
            logging.info("Discord embed sent ✓")
            return True
        else:
            logging.warning("Discord %d: %s", resp.status_code, resp.text[:150])
            return False
    except Exception as e:
        logging.error("Discord error: %s", e)
        return False


if __name__ == "__main__":
    ok = send_discord_alert("✅ MantleMind AI Discord bot is connected and working!")
    print("Sent:", ok)