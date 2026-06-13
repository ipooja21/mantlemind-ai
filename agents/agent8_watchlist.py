import os
import json
import logging
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent8] %(message)s")

WATCHLIST_FILE = "watchlist.json"

class WatchlistAgent:
    def __init__(self):
        self.watchlist = self._load()

    def _load(self):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                return json.load(f)
        except:
            return {}

    def _save(self):
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(self.watchlist, f, indent=2)

    def add_wallet(self, address: str, label: str = ""):
        address = address.lower().strip()
        self.watchlist[address] = {
            "label":    label or address[:10] + "...",
            "added":    datetime.now().isoformat(),
            "alerts":   [],
            "active":   True,
        }
        self._save()
        logging.info(f"Added to watchlist: {address[:20]}...")
        return True

    def remove_wallet(self, address: str):
        address = address.lower().strip()
        if address in self.watchlist:
            del self.watchlist[address]
            self._save()
            return True
        return False

    def scan(self, df: pd.DataFrame) -> list:
        
        if df.empty or not self.watchlist:
            return []

        alerts = []
        df_lower = df.copy()
        df_lower["from_lower"] = df["from"].str.lower()

        for address, info in self.watchlist.items():
            if not info.get("active"):
                continue
            matches = df_lower[df_lower["from_lower"] == address]
            if not matches.empty:
                total = matches["value_eth"].sum()
                alert = {
                    "address":   address,
                    "label":     info["label"],
                    "tx_count":  len(matches),
                    "total_eth": round(total, 4),
                    "time":      datetime.now().strftime("%H:%M:%S"),
                    "txns":      matches["hash"].tolist()[:3],
                }
                alerts.append(alert)
                self.watchlist[address]["alerts"].append(alert)
                logging.info(f"Watchlist hit: {info['label']} — {total:.4f} ETH")

        self._save()
        return alerts

    def get_all(self):
        return self.watchlist

    def get_count(self):
        return len(self.watchlist)