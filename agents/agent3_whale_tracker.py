import time
import numpy as np
import pandas as pd
from loguru import logger

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.config import WHALE_THRESHOLD_MNT



TIER_MEGA   = WHALE_THRESHOLD_MNT * 10     
TIER_LARGE  = WHALE_THRESHOLD_MNT          
TIER_MEDIUM = WHALE_THRESHOLD_MNT * 0.1   


class WhaleTrackerAgent:
    

    def __init__(self):
        self.whale_registry: dict[str, dict] = {}   
        logger.success("[WhaleTracker] Initialised")

    
    def detect_whales(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
        
        if df.empty:
            return df, []

        result = df.copy()
        result["is_whale_tx"] = False
        result["whale_score"] = 0.0
        result["whale_tier"] = "NONE"

        whale_mask = result["value_mnt"] >= TIER_MEDIUM
        result.loc[whale_mask, "is_whale_tx"] = True

        
        result.loc[whale_mask, "whale_score"] = result.loc[whale_mask].apply(
            self._compute_whale_score, axis=1
        )
        result.loc[whale_mask, "whale_tier"] = result.loc[whale_mask, "value_mnt"].apply(
            self._classify_tier
        )

        
        whale_wallets = self._build_wallet_profiles(result[whale_mask])

        
        alerts = self._build_alerts(whale_wallets, result)

        
        self.whale_registry.update(whale_wallets)

        n = len(whale_wallets)
        logger.info(f"[WhaleTracker] {n} unique whale wallets detected in this batch")
        return result, alerts

    
    def _compute_whale_score(self, row: pd.Series) -> float:
        
        value = row.get("value_mnt", 0)

        
        if value >= TIER_MEGA:
            base = 80.0
        elif value >= TIER_LARGE:
            base = 55.0
        else:
            base = 30.0

        
        anom_boost = float(row.get("anomaly_score", 0)) * 20.0

        
        contract_boost = 8.0 if row.get("is_contract_call", False) else 0.0

        
        wallet_freq = min(float(row.get("wallet_tx_count", 1)), 20.0)
        freq_boost = wallet_freq

        score = min(100.0, base + anom_boost + contract_boost + freq_boost)
        return round(score, 2)

    def _classify_tier(self, value_mnt: float) -> str:
        if value_mnt >= TIER_MEGA:
            return "MEGA"
        elif value_mnt >= TIER_LARGE:
            return "LARGE"
        return "MEDIUM"

    
    def _build_wallet_profiles(self, whale_df: pd.DataFrame) -> dict[str, dict]:
        
        profiles = {}
        if whale_df.empty:
            return profiles

        
        for addr, grp in whale_df.groupby("from_address"):
            total_sent = grp["value_mnt"].sum()
            avg_tx = grp["value_mnt"].mean()
            tx_count = len(grp)
            avg_score = grp["whale_score"].mean()
            tier = grp["whale_tier"].iloc[0]

            pattern = self._classify_pattern(grp, whale_df)

            profiles[addr] = {
                "address": addr,
                "total_sent_mnt": round(total_sent, 2),
                "avg_tx_mnt": round(avg_tx, 2),
                "tx_count": tx_count,
                "whale_score": round(avg_score, 2),
                "whale_tier": tier,
                "pattern": pattern,
                "last_seen": int(grp["timestamp"].max()) if "timestamp" in grp.columns else int(time.time()),
                "is_contract_user": bool(grp["is_contract_call"].any()),
            }

        return profiles

    
    def _classify_pattern(self, wallet_df: pd.DataFrame, full_df: pd.DataFrame) -> str:
        
        addr = wallet_df["from_address"].iloc[0]
        total_sent = wallet_df["value_mnt"].sum()
        total_received = full_df[full_df["to_address"] == addr]["value_mnt"].sum()

        n_unique_targets = wallet_df["to_address"].nunique()
        tx_count = len(wallet_df)

        if tx_count == 1 and total_sent > TIER_LARGE:
            return "TRANSFERRING"
        if n_unique_targets > 5 and tx_count > 3:
            return "ROTATING"
        if total_received > total_sent * 1.5:
            return "ACCUMULATING"
        if total_sent > total_received * 2:
            return "DISTRIBUTING"
        return "MIXED"

    
    def _build_alerts(self, profiles: dict, df: pd.DataFrame) -> list[dict]:
        
        alerts = []
        sorted_whales = sorted(profiles.values(), key=lambda x: x["whale_score"], reverse=True)

        for whale in sorted_whales[:10]:  
            alert = {
                "type": "WHALE",
                "timestamp": int(time.time()),
                "address": whale["address"],
                "tier": whale["whale_tier"],
                "score": whale["whale_score"],
                "pattern": whale["pattern"],
                "total_mnt": whale["total_sent_mnt"],
                "tx_count": whale["tx_count"],
                "message": (
                    f"🐋 *{whale['whale_tier']} Whale Detected*\n"
                    f"Address: `{whale['address'][:20]}…`\n"
                    f"Pattern: {whale['pattern']}\n"
                    f"Volume: {whale['total_sent_mnt']:,.0f} MNT\n"
                    f"Score: {whale['whale_score']}/100"
                ),
            }
            alerts.append(alert)

        return alerts

    
    def get_summary(self, whale_alerts: list[dict]) -> dict:
        if not whale_alerts:
            return {"total_whales": 0, "mega_whales": 0, "total_volume_mnt": 0.0, "top_pattern": "N/A"}

        return {
            "total_whales": len(whale_alerts),
            "mega_whales": sum(1 for w in whale_alerts if w.get("tier") == "MEGA"),
            "large_whales": sum(1 for w in whale_alerts if w.get("tier") == "LARGE"),
            "total_volume_mnt": round(sum(w.get("total_mnt", 0) for w in whale_alerts), 2),
            "avg_score": round(np.mean([w.get("score", 0) for w in whale_alerts]), 2),
            "top_pattern": max(
                set(w.get("pattern", "") for w in whale_alerts),
                key=lambda p: sum(1 for w in whale_alerts if w.get("pattern") == p),
            ),
        }



if __name__ == "__main__":
    sys.path.insert(0, "..")
    from agents.agent1_data_collector import DataCollectorAgent
    collector = DataCollectorAgent()
    df = collector.fetch_latest_blocks(10)
    tracker = WhaleTrackerAgent()
    df, alerts = tracker.detect_whales(df)
    print(f"Whale transactions: {df['is_whale_tx'].sum()}")
    for a in alerts[:3]:
        print(a["message"])
