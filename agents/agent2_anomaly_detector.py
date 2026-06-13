import os
import pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from loguru import logger

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.config import (
    ISO_FOREST_CONTAMINATION,
    ISO_FOREST_N_ESTIMATORS,
    ANOMALY_ALERT_THRESHOLD,
    MODEL_CACHE_FILE,
)



ANOMALY_FEATURES = [
    "log_value",
    "gas_price_gwei",
    "gas_cost_mnt",
    "value_to_gas_ratio",
    "value_zscore",
    "block_tx_count",
    "block_total_value",
    "wallet_tx_count",
    "is_contract_call",
    "is_large_tx",
]


class AnomalyDetectorAgent:
    

    def __init__(self):
        self.pipeline: Pipeline = self._build_pipeline()
        self.is_fitted: bool = False
        self._try_load_model()

    
    def _build_pipeline(self) -> Pipeline:
        
        return Pipeline([
            ("scaler", StandardScaler()),
            ("iso_forest", IsolationForest(
                n_estimators=ISO_FOREST_N_ESTIMATORS,
                contamination=ISO_FOREST_CONTAMINATION,
                max_features=1.0,
                bootstrap=False,
                n_jobs=-1,
                random_state=42,
            )),
        ])

    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        
        available = [f for f in ANOMALY_FEATURES if f in df.columns]
        missing = set(ANOMALY_FEATURES) - set(available)
        if missing:
            logger.debug(f"[AnomalyDetector] Missing features (will be 0): {missing}")

        X = df[available].copy()
        for f in missing:
            X[f] = 0.0

        X = X[ANOMALY_FEATURES]  # enforce order
        X = X.fillna(0).replace([np.inf, -np.inf], 0)
        return X

    
    def fit(self, df: pd.DataFrame):
        
        if len(df) < 20:
            logger.warning("[AnomalyDetector] Not enough data to train (need ≥20 rows)")
            return

        X = self._prepare_features(df)
        logger.info(f"[AnomalyDetector] Training on {len(X)} samples, {X.shape[1]} features")
        self.pipeline.fit(X)
        self.is_fitted = True
        self._save_model()
        logger.success("[AnomalyDetector] Model trained and saved")

    
    def score(self, df: pd.DataFrame) -> pd.DataFrame:
        
        if df.empty:
            return df

        result = df.copy()

        if not self.is_fitted:
            logger.info("[AnomalyDetector] Model not fitted — fitting now on current data")
            self.fit(df)

        X = self._prepare_features(df)

        
        raw_scores = self.pipeline.decision_function(X)

        
        score_min, score_max = raw_scores.min(), raw_scores.max()
        if score_max > score_min:
            normalised = 1 - (raw_scores - score_min) / (score_max - score_min)
        else:
            normalised = np.zeros(len(raw_scores))

        
        labels = self.pipeline.predict(X)

        result["anomaly_score"] = np.round(normalised, 4)
        result["is_anomaly"] = labels == -1

        result["risk_level"] = pd.cut(
            result["anomaly_score"],
            bins=[0, 0.4, 0.6, 0.8, 1.0],
            labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            include_lowest=True,
        )

        n_anomalies = result["is_anomaly"].sum()
        logger.info(f"[AnomalyDetector] Scored {len(result)} txs — {n_anomalies} anomalies detected")
        return result

    
    def get_summary(self, scored_df: pd.DataFrame) -> dict:
        
        if "anomaly_score" not in scored_df.columns or scored_df.empty:
            return {}

        anom = scored_df[scored_df["is_anomaly"] == True]
        risk_counts = scored_df["risk_level"].value_counts().to_dict() if "risk_level" in scored_df.columns else {}

        top_anomalies = []
        if not anom.empty:
            top = anom.nlargest(5, "anomaly_score")
            for _, row in top.iterrows():
                top_anomalies.append({
                    "tx_hash": str(row.get("tx_hash", ""))[:18] + "…",
                    "from": str(row.get("from_address", ""))[:14] + "…",
                    "value_mnt": round(float(row.get("value_mnt", 0)), 2),
                    "anomaly_score": round(float(row["anomaly_score"]), 4),
                    "risk_level": str(row.get("risk_level", "UNKNOWN")),
                })

        return {
            "total_transactions": len(scored_df),
            "total_anomalies": int(scored_df["is_anomaly"].sum()),
            "anomaly_rate": round(scored_df["is_anomaly"].mean() * 100, 2),
            "avg_anomaly_score": round(float(scored_df["anomaly_score"].mean()), 4),
            "max_anomaly_score": round(float(scored_df["anomaly_score"].max()), 4),
            "risk_distribution": {str(k): int(v) for k, v in risk_counts.items()},
            "top_anomalies": top_anomalies,
            "critical_count": int((scored_df["anomaly_score"] >= ANOMALY_ALERT_THRESHOLD).sum()),
        }

    
    def _save_model(self):
        try:
            with open(MODEL_CACHE_FILE, "wb") as f:
                pickle.dump(self.pipeline, f)
            logger.debug("[AnomalyDetector] Model saved to disk")
        except Exception as e:
            logger.warning(f"[AnomalyDetector] Model save failed: {e}")

    def _try_load_model(self):
        if os.path.exists(MODEL_CACHE_FILE):
            try:
                with open(MODEL_CACHE_FILE, "rb") as f:
                    self.pipeline = pickle.load(f)
                self.is_fitted = True
                logger.success("[AnomalyDetector] Pre-trained model loaded from cache")
            except Exception as e:
                logger.warning(f"[AnomalyDetector] Model load failed: {e} — will retrain")



if __name__ == "__main__":
    from agent1_data_collector import DataCollectorAgent
    collector = DataCollectorAgent()
    df = collector.fetch_latest_blocks(n_blocks=10)
    detector = AnomalyDetectorAgent()
    scored = detector.score(df)
    print(scored[["value_mnt", "anomaly_score", "is_anomaly", "risk_level"]].head(10))
    print(detector.get_summary(scored))
