import time
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [Pipeline] %(message)s")


class MantleMindPipeline:

    def __init__(self):
        from agents.agent1_data_collector   import DataCollectorAgent
        from agents.agent2_anomaly_detector import AnomalyDetectorAgent
        from agents.agent3_whale_tracker    import WhaleTrackerAgent
        from agents.agent4_alpha_generator  import AlphaGeneratorAgent
        from agents.agent5_alert_agent      import AlertAgent
        from agents.agent6_report_agent     import ReportAgent
        from agents.agent7_llm              import LLMIntelligenceAgent
        from agents.agent8_watchlist        import WatchlistAgent
        from agents.agent9_wallet_clustering import WalletClusteringAgent
        from agents.agent10_mev_detector    import MEVDetectorAgent

        logging.info("Initialising all agents...")
        self.collector       = DataCollectorAgent()
        self.anomaly         = AnomalyDetectorAgent()
        self.whale           = WhaleTrackerAgent()
        self.alpha_gen       = AlphaGeneratorAgent()
        self.alert           = AlertAgent()
        self.reporter        = ReportAgent()
        self.llm             = LLMIntelligenceAgent()
        self.watchlist_agent = WatchlistAgent()
        self.clustering_agent = WalletClusteringAgent()
        self.mev_agent        = MEVDetectorAgent()

        self._last_state    = None
        self._alpha_history = []
        logging.info("All 10 agents ready ✓")

    
    def run(self, n_blocks: int = 20) -> dict:
        t0 = time.time()
        logging.info("Pipeline start — %d blocks", n_blocks)

        
        net_stats = self.collector.get_network_stats()
        df_raw    = self.collector.fetch_latest_blocks(n_blocks)

        if not df_raw.empty:
            df = df_raw.rename(columns={
                "hash":      "tx_hash",
                "from":      "from_address",
                "to":        "to_address",
                "value_eth": "value_mnt",
                "block":     "block_number",
            })
            df["is_contract_call"] = df["to_address"].apply(
                lambda x: x == "contract_creation" or
                          (isinstance(x, str) and x.startswith("0x"))
            )
        else:
            df = pd.DataFrame(columns=[
                "block_number","tx_hash","from_address","to_address",
                "value_mnt","gas","gas_price_gwei","is_contract_call","timestamp",
            ])

        
        if not df.empty:
            df_work = df.rename(columns={
                "from_address":  "from",
                "tx_hash":       "hash",
                "value_mnt":     "value_eth",
                "gas_price_gwei":"gas_price",
            })
            scored = self.anomaly.score(df_work)
            if not scored.empty:
                df["anomaly_score"] = scored["anomaly_score"].values
                df["risk_level"]    = scored["risk_level"].astype(str).values
                df["is_anomaly"]    = scored["is_anomaly"].values
                
                df["is_anomaly"] = df["is_anomaly"] | df["risk_level"].isin(["HIGH", "CRITICAL"])
            else:
                df["anomaly_score"] = 0.0
                df["risk_level"]    = "LOW"
                df["is_anomaly"]    = False
        else:
            df["anomaly_score"] = 0.0
            df["risk_level"]    = "LOW"
            df["is_anomaly"]    = False

        total_anom = int(df["is_anomaly"].sum()) if "is_anomaly" in df.columns else 0
        crit_count = int((df["risk_level"] == "CRITICAL").sum()) if "risk_level" in df.columns else 0
        anom_rate  = (total_anom / max(len(df), 1)) * 100

        top_anomalies = []
        if total_anom > 0:
            for _, row in df[df["is_anomaly"] == True].nlargest(5, "anomaly_score").iterrows():
                top_anomalies.append({
                    "tx_hash":       str(row.get("tx_hash",""))[:20] + "...",
                    "from":          str(row.get("from_address",""))[:16] + "...",
                    "value_mnt":     round(float(row.get("value_mnt", 0)), 4),
                    "anomaly_score": round(float(row.get("anomaly_score", 0)), 4),
                })

        anomaly_summary = {
            "total_anomalies": total_anom,
            "critical_count":  crit_count,
            "anomaly_rate":    round(anom_rate, 2),
            "top_anomalies":   top_anomalies,
            "avg_anomaly_score": round(float(df["anomaly_score"].mean()), 4) if not df.empty else 0,
            "max_anomaly_score": round(float(df["anomaly_score"].max()), 4) if not df.empty else 0,
        }

        
        whale_alerts = []
        try:
            whale_result, raw_alerts = self.whale.detect_whales(df.copy())
            if raw_alerts:
                df["is_whale_tx"] = whale_result["is_whale_tx"].values if "is_whale_tx" in whale_result.columns else False
                for a in raw_alerts:
                    whale_alerts.append({
                        "address":   str(a.get("address", "")),
                        "tier":      str(a.get("tier", "MEDIUM")),
                        "pattern":   str(a.get("pattern", "TRANSFERRING")),
                        "total_mnt": float(a.get("total_mnt", 0)),
                        "score":     float(a.get("score", 0)),
                        "tx_count":  int(a.get("tx_count", 1)),
                    })
            else:
                df["is_whale_tx"] = False
        except Exception as e:
            logging.warning("Whale tracker error: %s", e)
            df["is_whale_tx"] = False

        whale_summary = self.whale.get_summary(whale_alerts)

        
        try:
            os.makedirs("data", exist_ok=True)
            df.to_csv(os.path.join("data", "tx_cache.csv"), index=False)
        except Exception as e:
            logging.warning("tx_cache.csv save error: %s", e)

        
        try:
            wallet_clusters = self.clustering_agent.run()
        except Exception as e:
            logging.warning("Agent 9 (clustering) error: %s", e)
            wallet_clusters = []

        
        try:
            mev_alerts = self.mev_agent.run()
        except Exception as e:
            logging.warning("Agent 10 (MEV) error: %s", e)
            mev_alerts = []

        
        try:
            df_for_watchlist = df.rename(columns={
                "from_address":"from","tx_hash":"hash",
                "value_mnt":"value_eth","gas_price_gwei":"gas_price",
            })
            watchlist_alerts = self.watchlist_agent.scan(df_for_watchlist)
        except Exception as e:
            logging.warning("Watchlist error: %s", e)
            watchlist_alerts = []

        
        df_for_alpha = df.rename(columns={
            "from_address":"from","tx_hash":"hash",
            "value_mnt":"value_eth","gas_price_gwei":"gas_price",
        })
        try:
            alpha_raw = self.alpha_gen.generate(df_for_alpha, anomaly_summary, whale_alerts)
        except Exception as e:
            logging.warning("Alpha gen error: %s", e)
            alpha_raw = {"alpha_score": 50, "signal": "NEUTRAL", "components": {}, "confidence": "Low"}

        alpha_score  = alpha_raw.get("alpha_score", 50)
        signal_raw   = alpha_raw.get("signal", "NEUTRAL")

        
        signal_clean = (
            str(signal_raw)
            .replace("🚀 Strong Bullish","STRONG_BULL")
            .replace("📈 Bullish","BULL")
            .replace("➡️ Neutral","NEUTRAL")
            .replace("➡️  Neutral","NEUTRAL")
            .replace("📉 Bearish","BEAR")
            .replace("🔻 Strong Bearish","STRONG_BEAR")
            .strip()
        )
        if signal_clean not in ("STRONG_BULL","BULL","NEUTRAL","BEAR","STRONG_BEAR"):
            signal_clean = "NEUTRAL"

        emoji_map = {"STRONG_BULL":"🚀","BULL":"📈","NEUTRAL":"➡️","BEAR":"📉","STRONG_BEAR":"🔻"}

        raw_comps = alpha_raw.get("components", {})
        gas_val   = float(net_stats.get("gas_price_gwei", 1))
        components = {
            "whale_signal":      float(raw_comps.get("whale_signal", 0)),
            "volume_trend":      float(raw_comps.get("volume_trend", 0)),
            "gas_momentum":      min(float(raw_comps.get("gas_momentum", gas_val)), 100),
            "contract_activity": float(raw_comps.get("contract_activity", 0)),
            "anomaly_penalty":   float(raw_comps.get("anomaly_penalty", 0)),
        }

        
        try:
            narrative = self.llm.generate_insight(
                alpha_result=alpha_raw,
                whale_count=len(whale_alerts),
                anomaly_count=total_anom,
                tx_count=len(df),
                top_anomaly_score=float(df["anomaly_score"].max()) if not df.empty else 0,
            )
        except Exception as e:
            logging.warning("LLM agent skipped: %s", e)
            narrative = alpha_raw.get("narrative", "Analysis complete.")

        alpha = {
            "alpha_score": alpha_score,
            "signal":      signal_clean,
            "emoji":       emoji_map.get(signal_clean, "➡️"),
            "confidence":  alpha_raw.get("confidence", "Medium"),
            "components":  components,
            "narrative":   narrative,
            "is_alert":    alpha_raw.get("is_alert", False),
            "tx_count":    len(df),
        }

        self._alpha_history.append({
            "timestamp":   int(time.time()),
            "alpha_score": alpha_score,
            "signal":      signal_clean,
        })
        alpha_history_df = pd.DataFrame(self._alpha_history[-50:])

        
        try:
            from signal_history import log_signal
            log_signal(alpha_score, signal_clean)
        except Exception as e:
            logging.warning("Signal history log error: %s", e)

        
        try:
            self.alert.send_alpha_alert(alpha)
            self.alert.send_anomaly_alert(anomaly_summary)
            for w in whale_alerts[:3]:
                self.alert.send_whale_alert(w)
        except Exception as e:
            logging.warning("Alert agent error: %s", e)

        try:
            recent_alerts = [
                {
                    "type":      a.get("type", "INFO"),
                    "timestamp": a.get("timestamp", int(time.time())),
                    "message":   a.get("message", ""),
                }
                for a in self.alert.get_recent_alerts(20)
            ]
        except Exception:
            recent_alerts = []

        elapsed = round(time.time() - t0, 2)

        state = {
            "df":               df,
            "network_stats":    {**net_stats, "chain_id": 5000, "mode": "live"},
            "anomaly_summary":  anomaly_summary,
            "whale_alerts":     whale_alerts,
            "whale_summary":    whale_summary,
            "alpha":            alpha,
            "recent_alerts":    recent_alerts,
            "alpha_history":    alpha_history_df,
            "watchlist_alerts": watchlist_alerts,
            "wallet_clusters":  wallet_clusters,
            "mev_alerts":       mev_alerts,
            "run_timestamp":    int(time.time()),
            "elapsed":          elapsed,
        }
        self._last_state = state
        logging.info("Pipeline done in %ss | Alpha: %s | %s | Clusters: %d | MEV: %d",
                      elapsed, alpha_score, signal_clean, len(wallet_clusters), len(mev_alerts))
        return state

    
    def chat(self, question: str) -> str:
        if not self._last_state:
            return "Pehle analysis run karo."
        s = self._last_state
        context = {
            "alpha_score":    s["alpha"]["alpha_score"],
            "signal":         s["alpha"]["signal"],
            "whale_count":    len(s["whale_alerts"]),
            "anomaly_count":  s["anomaly_summary"]["total_anomalies"],
            "anomaly_rate":   s["anomaly_summary"]["anomaly_rate"],
            "tx_count":       len(s["df"]),
            "latest_block":   s["network_stats"].get("latest_block", 0),
        }
        try:
            return self.llm.chat_with_data(question, context)
        except Exception as e:
            return f"Chat error: {e}"

    
    def generate_reports(self) -> dict:
        if not self._last_state:
            return {"pdf": None, "excel": None}
        try:
            s  = self._last_state
            df = s["df"]
            rename_map = {
                "from_address":"from","tx_hash":"hash",
                "value_mnt":"value_eth","gas_price_gwei":"gas_price",
            }
            alpha_result = {
                "alpha_score":    s["alpha"]["alpha_score"],
                "signal":         s["alpha"]["signal"],
                "confidence":     s["alpha"]["confidence"],
                "narrative":      s["alpha"]["narrative"],
                "components":     s["alpha"]["components"],
                "top_insight":    s["alpha"]["narrative"][:100],
                "recommendation": "See full report for details.",
            }

            pdf_path = self.reporter.generate_pdf(
                df.rename(columns=rename_map),
                s["anomaly_summary"],
                s["whale_alerts"],
                alpha_result,
                s["network_stats"],
            )
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            xlsx_path = self.reporter.generate_excel(
                df.rename(columns=rename_map),
                s["anomaly_summary"],
                s["whale_alerts"],
                alpha_result,
                s["network_stats"],
            )
            with open(xlsx_path, "rb") as f:
                xlsx_bytes = f.read()

            return {"pdf": pdf_bytes, "excel": xlsx_bytes}
        except Exception as e:
            logging.error("Report error: %s", e)
            return {"pdf": None, "excel": None}