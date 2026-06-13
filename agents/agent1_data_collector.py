import time
import json
import asyncio
from typing import Optional
import pandas as pd
import numpy as np
from web3 import Web3
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from core.config import (
    MANTLE_RPC_URL, BLOCKS_PER_FETCH, WEI_TO_MNT, DATA_CACHE_FILE
)


class DataCollectorAgent:
    

    def __init__(self):
        self.w3: Optional[Web3] = None
        self.cache: pd.DataFrame = pd.DataFrame()
        self._connect()

    # ─── RPC Connection 
    def _connect(self):
        
        try:
            self.w3 = Web3(Web3.HTTPProvider(MANTLE_RPC_URL, request_kwargs={"timeout": 30}))
            if self.w3.is_connected():
                chain = self.w3.eth.chain_id
                logger.success(f"[DataCollector] Connected to Mantle (chain_id={chain})")
            else:
                logger.warning("[DataCollector] RPC connected but is_connected=False — using mock mode")
                self.w3 = None
        except Exception as e:
            logger.error(f"[DataCollector] RPC connection failed: {e} — using mock mode")
            self.w3 = None

    
    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _get_block(self, block_number: int) -> dict:
        """Fetch a single block with full transaction objects."""
        return self.w3.eth.get_block(block_number, full_transactions=True)

    
    def fetch_latest_blocks(self, n_blocks: int = BLOCKS_PER_FETCH) -> pd.DataFrame:
        
        if self.w3 is None:
            logger.warning("[DataCollector] RPC offline — generating mock data for demo")
            return self._generate_mock_data(n_blocks)

        try:
            latest = self.w3.eth.block_number
            start = max(0, latest - n_blocks + 1)
            logger.info(f"[DataCollector] Fetching blocks {start} → {latest}")

            records = []
            for bn in range(start, latest + 1):
                try:
                    block = self._get_block(bn)
                    ts = block.get("timestamp", int(time.time()))
                    for tx in block.get("transactions", []):
                        records.append(self._parse_tx(tx, bn, ts))
                except Exception as e:
                    logger.warning(f"[DataCollector] Block {bn} failed: {e}")
                    continue

            if not records:
                logger.warning("[DataCollector] No transactions found — using mock")
                return self._generate_mock_data(n_blocks)

            df = pd.DataFrame(records)
            df = self._engineer_features(df)
            self._update_cache(df)
            logger.success(f"[DataCollector] Fetched {len(df)} transactions from {n_blocks} blocks")
            return df

        except Exception as e:
            logger.error(f"[DataCollector] fetch_latest_blocks error: {e}")
            return self._generate_mock_data(n_blocks)

    
    def _parse_tx(self, tx: dict, block_number: int, timestamp: int) -> dict:
        """Extract structured fields from a raw transaction."""
        value_mnt = int(tx.get("value", 0)) / WEI_TO_MNT
        gas_price_gwei = int(tx.get("gasPrice", 0)) / 1e9
        gas_used = int(tx.get("gas", 21000))

        return {
            "block_number": block_number,
            "timestamp": timestamp,
            "tx_hash": tx.get("hash", b"").hex() if hasattr(tx.get("hash", ""), "hex") else str(tx.get("hash", "")),
            "from_address": tx.get("from", "0x0000"),
            "to_address": tx.get("to", "0x0000") or "0x0000",  # contract creation → 0x0000
            "value_mnt": value_mnt,
            "gas_price_gwei": gas_price_gwei,
            "gas_limit": gas_used,
            "is_contract_call": bool(tx.get("input", "0x") not in ["0x", "", None, b""]),
            "nonce": int(tx.get("nonce", 0)),
        }

    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        
        if df.empty:
            return df

        df = df.copy()
        df["log_value"] = np.log1p(df["value_mnt"])
        df["gas_cost_mnt"] = (df["gas_price_gwei"] * df["gas_limit"]) / 1e9
        df["value_to_gas_ratio"] = df["value_mnt"] / (df["gas_cost_mnt"] + 1e-9)
        df["is_large_tx"] = (df["value_mnt"] > df["value_mnt"].quantile(0.95)).astype(int)

        
        block_stats = df.groupby("block_number").agg(
            block_tx_count=("tx_hash", "count"),
            block_total_value=("value_mnt", "sum"),
            block_avg_gas=("gas_price_gwei", "mean"),
        ).reset_index()
        df = df.merge(block_stats, on="block_number", how="left")

        
        mu = df["value_mnt"].mean()
        sigma = df["value_mnt"].std() + 1e-9
        df["value_zscore"] = (df["value_mnt"] - mu) / sigma

        
        wallet_counts = df["from_address"].value_counts().rename("wallet_tx_count")
        df = df.join(wallet_counts, on="from_address")

        df["fetched_at"] = int(time.time())
        return df

    
    def _update_cache(self, new_df: pd.DataFrame):
        
        try:
            if os.path.exists(DATA_CACHE_FILE):
                existing = pd.read_csv(DATA_CACHE_FILE)
                combined = pd.concat([existing, new_df], ignore_index=True)
                
                if "tx_hash" in combined.columns:
                    combined = combined.drop_duplicates(subset=["tx_hash"])
                combined = combined.tail(10000)  # rolling 10k window
            else:
                combined = new_df

            combined.to_csv(DATA_CACHE_FILE, index=False)
            self.cache = combined
            logger.debug(f"[DataCollector] Cache updated — {len(combined)} total rows")
        except Exception as e:
            logger.warning(f"[DataCollector] Cache update failed: {e}")

    def load_cache(self) -> pd.DataFrame:
        
        if os.path.exists(DATA_CACHE_FILE):
            df = pd.read_csv(DATA_CACHE_FILE)
            self.cache = df
            return df
        return pd.DataFrame()

    
    def _generate_mock_data(self, n_blocks: int = 20) -> pd.DataFrame:
        
        np.random.seed(int(time.time()) % 10000)
        n_tx = n_blocks * np.random.randint(8, 25)
        latest_block = 65000000 + np.random.randint(0, 1000)

        addresses = [f"0x{os.urandom(20).hex()}" for _ in range(30)]

        
        values = np.random.lognormal(mean=2.0, sigma=2.5, size=n_tx)
        whale_mask = np.random.random(n_tx) < 0.05
        values[whale_mask] *= np.random.uniform(500, 2000, whale_mask.sum())

        records = []
        for i in range(n_tx):
            records.append({
                "block_number": latest_block - (n_tx - i) // 15,
                "timestamp": int(time.time()) - (n_tx - i) * 3,
                "tx_hash": f"0x{os.urandom(32).hex()}",
                "from_address": np.random.choice(addresses),
                "to_address": np.random.choice(addresses),
                "value_mnt": round(values[i], 4),
                "gas_price_gwei": round(np.random.uniform(0.001, 0.1), 6),
                "gas_limit": int(np.random.choice([21000, 65000, 150000, 300000])),
                "is_contract_call": bool(np.random.random() < 0.35),
                "nonce": int(np.random.randint(0, 500)),
            })

        df = pd.DataFrame(records)
        df = self._engineer_features(df)
        self._update_cache(df)
        logger.info(f"[DataCollector] Mock data: {len(df)} txs across {n_blocks} blocks")
        return df

    
    def get_network_stats(self) -> dict:
        
        if self.w3 is None:
            return {
                "connected": False,
                "latest_block": 65_000_000 + np.random.randint(0, 9999),
                "gas_price_gwei": round(np.random.uniform(0.001, 0.05), 6),
                "chain_id": 5000,
                "mode": "demo",
            }
        try:
            return {
                "connected": True,
                "latest_block": self.w3.eth.block_number,
                "gas_price_gwei": round(self.w3.eth.gas_price / 1e9, 6),
                "chain_id": self.w3.eth.chain_id,
                "mode": "live",
            }
        except Exception as e:
            logger.error(f"[DataCollector] get_network_stats: {e}")
            return {"connected": False, "mode": "error"}



if __name__ == "__main__":
    agent = DataCollectorAgent()
    df = agent.fetch_latest_blocks(n_blocks=5)
    print(df[["block_number", "value_mnt", "log_value", "value_zscore"]].head(10))
    print(agent.get_network_stats())
