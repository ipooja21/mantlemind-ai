import os
import json
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent10] %(message)s")

DATA_DIR = "data"
TX_CACHE = os.path.join(DATA_DIR, "tx_cache.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "mev_alerts.json")


HIGH_GAS_PERCENTILE = 0.75


class MEVDetectorAgent:
    def __init__(self, tx_cache_path: str = TX_CACHE):
        self.tx_cache_path = tx_cache_path

    def load_data(self) -> pd.DataFrame:
        if not os.path.exists(self.tx_cache_path):
            logging.warning("tx_cache.csv not found")
            return pd.DataFrame()
        df = pd.read_csv(self.tx_cache_path)
        for col in ["block_number", "tx_hash", "from_address", "to_address",
                     "value_mnt", "gas_price_gwei"]:
            if col not in df.columns:
                df[col] = None
        return df.dropna(subset=["block_number", "from_address", "to_address", "gas_price_gwei"])

    def run(self) -> list:
        df = self.load_data()
        if df.empty:
            self._save([])
            return []

        alerts = []

        for block, group in df.groupby("block_number"):
            if len(group) < 3:
                continue

            gas_threshold = group["gas_price_gwei"].quantile(HIGH_GAS_PERCENTILE)
            group = group.sort_index()  # preserve in-block ordering as proxy for tx index

            rows = group.to_dict("records")

            for i in range(len(rows) - 2):
                a, v, b = rows[i], rows[i + 1], rows[i + 2]

                same_target = a["to_address"] == v["to_address"] == b["to_address"]
                same_attacker = a["from_address"] == b["from_address"] and a["from_address"] != v["from_address"]
                a_high = a["gas_price_gwei"] >= gas_threshold
                b_high = b["gas_price_gwei"] >= gas_threshold
                v_lower = v["gas_price_gwei"] < a["gas_price_gwei"] and v["gas_price_gwei"] < b["gas_price_gwei"]

                if same_target and same_attacker and a_high and b_high and v_lower:
                    alerts.append({
                        "block_number": int(block),
                        "attacker_wallet": a["from_address"],
                        "victim_wallet": v["from_address"],
                        "target_contract": a["to_address"],
                        "front_run_tx": a["tx_hash"],
                        "victim_tx": v["tx_hash"],
                        "back_run_tx": b["tx_hash"],
                        "attacker_gas_gwei": round(float(a["gas_price_gwei"]), 4),
                        "victim_gas_gwei": round(float(v["gas_price_gwei"]), 4),
                        "estimated_victim_value_mnt": float(v.get("value_mnt", 0) or 0),
                        "confidence": "HIGH" if (a_high and b_high) else "MEDIUM",
                    })

        self._save(alerts)
        logging.info("Detected %d potential MEV sandwich attack(s)", len(alerts))
        return alerts

    def _save(self, alerts: list):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(alerts, f, indent=2, default=str)


if __name__ == "__main__":
    agent = MEVDetectorAgent()
    result = agent.run()
    print(json.dumps(result, indent=2, default=str))