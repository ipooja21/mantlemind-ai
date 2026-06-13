import time
import numpy as np
import pandas as pd
from loguru import logger

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.config import ALPHA_ALERT_THRESHOLD



def _label(score: float) -> str:
    if score >= 80: return "STRONG_BULL"
    if score >= 60: return "BULL"
    if score >= 40: return "NEUTRAL"
    if score >= 20: return "BEAR"
    return "STRONG_BEAR"

def _emoji(signal: str) -> str:
    return {
        "STRONG_BULL": "🚀",
        "BULL": "📈",
        "NEUTRAL": "➡️",
        "BEAR": "📉",
        "STRONG_BEAR": "🩸",
    }.get(signal, "❓")


class AlphaGeneratorAgent:
    

    def __init__(self):
        self.history: list[dict] = []
        logger.success("[AlphaGenerator] Initialised")

    
    def generate(
        self,
        df: pd.DataFrame,
        anomaly_summary: dict,
        whale_alerts: list[dict],
    ) -> dict:
        
        if df.empty:
            return self._empty_alpha()

        components = {
            "whale_signal":     self._score_whale_signal(df, whale_alerts),
            "anomaly_penalty":  self._score_anomaly_penalty(anomaly_summary),
            "volume_trend":     self._score_volume_trend(df),
            "gas_momentum":     self._score_gas_momentum(df),
            "contract_activity":self._score_contract_activity(df),
        }

        weights = {
            "whale_signal":     0.35,
            "anomaly_penalty":  0.25,   # subtracted
            "volume_trend":     0.20,
            "gas_momentum":     0.10,
            "contract_activity":0.10,
        }

        
        raw = (
            components["whale_signal"]      * weights["whale_signal"]
            - components["anomaly_penalty"] * weights["anomaly_penalty"]  # penalty
            + components["volume_trend"]    * weights["volume_trend"]
            + components["gas_momentum"]    * weights["gas_momentum"]
            + components["contract_activity"]* weights["contract_activity"]
        )

        
        alpha_score = float(np.clip(raw, 0, 100))
        signal = _label(alpha_score)

        narrative = self._generate_narrative(alpha_score, signal, components, whale_alerts, anomaly_summary, df)

        result = {
            "timestamp": int(time.time()),
            "alpha_score": round(alpha_score, 1),
            "signal": signal,
            "emoji": _emoji(signal),
            "narrative": narrative,
            "components": {k: round(float(v), 2) for k, v in components.items()},
            "is_alert": alpha_score >= ALPHA_ALERT_THRESHOLD,
            "tx_count": len(df),
            "blocks_analysed": int(df["block_number"].nunique()) if "block_number" in df.columns else 0,
        }

        self.history.append(result)
        if len(self.history) > 100:
            self.history = self.history[-100:]

        logger.info(f"[AlphaGenerator] Score={alpha_score:.1f} | Signal={signal}")
        return result

    
    def _score_whale_signal(self, df: pd.DataFrame, whale_alerts: list[dict]) -> float:
        
        if not whale_alerts:
            return 50.0  # neutral

        patterns = [w.get("pattern", "") for w in whale_alerts]
        scores = [w.get("score", 0) for w in whale_alerts]

        acc = sum(s for p, s in zip(patterns, scores) if p == "ACCUMULATING")
        dist = sum(s for p, s in zip(patterns, scores) if p == "DISTRIBUTING")
        total = sum(scores) + 1e-9

        bull_ratio = acc / total
        bear_ratio = dist / total

        return float(np.clip(50.0 + (bull_ratio - bear_ratio) * 50.0, 0, 100))

    def _score_anomaly_penalty(self, summary: dict) -> float:
        
        rate = summary.get("anomaly_rate", 0)
        critical = summary.get("critical_count", 0)
        penalty = rate * 0.8 + min(critical * 5, 40)
        return float(np.clip(penalty, 0, 100))

    def _score_volume_trend(self, df: pd.DataFrame) -> float:
        
        if "value_mnt" not in df.columns or len(df) < 10:
            return 50.0
        mid = len(df) // 2
        old_vol = df.iloc[:mid]["value_mnt"].sum()
        new_vol = df.iloc[mid:]["value_mnt"].sum()
        ratio = new_vol / (old_vol + 1e-9)
        score = np.clip(50.0 * ratio, 0, 100)
        return float(score)

    def _score_gas_momentum(self, df: pd.DataFrame) -> float:
        
        if "gas_price_gwei" not in df.columns or len(df) < 4:
            return 50.0
        recent = df["gas_price_gwei"].tail(len(df) // 3).mean()
        overall = df["gas_price_gwei"].mean()
        ratio = recent / (overall + 1e-12)
        
        if ratio < 0.5:
            return 25.0
        elif ratio <= 1.5:
            return 70.0 + (ratio - 1.0) * 20.0
        else:
            return max(30.0, 90.0 - (ratio - 1.5) * 20.0)

    def _score_contract_activity(self, df: pd.DataFrame) -> float:
        
        if "is_contract_call" not in df.columns:
            return 50.0
        ratio = df["is_contract_call"].mean()
        return float(np.clip(40.0 + ratio * 60.0, 0, 100))

    
    def _generate_narrative(
        self,
        score: float,
        signal: str,
        components: dict,
        whale_alerts: list[dict],
        anomaly_summary: dict,
        df: pd.DataFrame,
    ) -> str:
        
        lines = []
        emoji = _emoji(signal)

        lines.append(f"{emoji} **Mantle Network Alpha: {signal}** (Score: {score:.0f}/100)")
        lines.append("")

        
        vol_total = round(df["value_mnt"].sum(), 0) if "value_mnt" in df.columns else 0
        lines.append(f"📊 **On-chain Volume:** {vol_total:,.0f} MNT across {len(df)} transactions.")

        
        n_whales = len(whale_alerts)
        if n_whales > 0:
            mega = sum(1 for w in whale_alerts if w.get("tier") == "MEGA")
            top_pattern = max(set(w.get("pattern","") for w in whale_alerts), key=lambda p: sum(1 for w in whale_alerts if w.get("pattern")==p))
            lines.append(f"🐋 **Whale Activity:** {n_whales} whale wallets detected ({mega} MEGA). "
                         f"Dominant pattern: **{top_pattern}**.")
        else:
            lines.append("🐋 **Whale Activity:** No significant whale movement in this window.")

        
        anom_rate = anomaly_summary.get("anomaly_rate", 0)
        crit = anomaly_summary.get("critical_count", 0)
        if anom_rate > 10:
            lines.append(f"⚠️ **Anomaly Alert:** {anom_rate:.1f}% anomaly rate with {crit} critical transactions. "
                         f"Elevated risk detected.")
        elif anom_rate > 3:
            lines.append(f"🔍 **Anomalies:** Moderate anomaly rate ({anom_rate:.1f}%). Monitor closely.")
        else:
            lines.append(f"✅ **Network Health:** Low anomaly rate ({anom_rate:.1f}%). Network operating normally.")

       
        lines.append("")
        if signal in ("STRONG_BULL", "BULL"):
            lines.append("💡 **Insight:** Smart money inflows and strong volume suggest near-term bullish momentum "
                         "on Mantle. Consider monitoring DeFi protocols for increased activity.")
        elif signal in ("STRONG_BEAR", "BEAR"):
            lines.append("💡 **Insight:** Distribution patterns and elevated anomalies suggest caution. "
                         "Smart money appears to be reducing exposure on Mantle.")
        else:
            lines.append("💡 **Insight:** Mixed signals. Market is consolidating. Watch whale patterns "
                         "for the next directional move.")

        return "\n".join(lines)

    def _empty_alpha(self) -> dict:
        return {
            "timestamp": int(time.time()),
            "alpha_score": 50.0,
            "signal": "NEUTRAL",
            "emoji": "➡️",
            "narrative": "Insufficient data to generate alpha signal.",
            "components": {},
            "is_alert": False,
            "tx_count": 0,
            "blocks_analysed": 0,
        }

    
    def get_history_df(self) -> pd.DataFrame:
        
        if not self.history:
            return pd.DataFrame()
        rows = []
        for h in self.history:
            rows.append({
                "timestamp": h["timestamp"],
                "alpha_score": h["alpha_score"],
                "signal": h["signal"],
            })
        return pd.DataFrame(rows)



if __name__ == "__main__":
    from agent1_data_collector import DataCollectorAgent
    from agent2_anomaly_detector import AnomalyDetectorAgent
    from agent3_whale_tracker import WhaleTrackerAgent

    collector = DataCollectorAgent()
    detector  = AnomalyDetectorAgent()
    tracker   = WhaleTrackerAgent()
    generator = AlphaGeneratorAgent()

    df = collector.fetch_latest_blocks(10)
    df = detector.score(df)
    anom_summary = detector.get_summary(df)
    df, whale_alerts = tracker.detect_whales(df)

    alpha = generator.generate(df, anom_summary, whale_alerts)
    print(alpha["narrative"])
    print(f"\nAlpha Score: {alpha['alpha_score']}")
