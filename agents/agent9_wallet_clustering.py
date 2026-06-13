import os
import json
import logging
import pandas as pd
from collections import defaultdict
from itertools import combinations

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Agent9] %(message)s")

DATA_DIR = "data"
TX_CACHE = os.path.join(DATA_DIR, "tx_cache.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "wallet_clusters.json")


class WalletClusteringAgent:
    def __init__(self, tx_cache_path: str = TX_CACHE):
        self.tx_cache_path = tx_cache_path

    def load_data(self) -> pd.DataFrame:
        if not os.path.exists(self.tx_cache_path):
            logging.warning("tx_cache.csv not found — returning empty dataframe")
            return pd.DataFrame()
        df = pd.read_csv(self.tx_cache_path)
        # Normalize expected columns
        for col in ["from_address", "to_address", "gas_price_gwei", "value_mnt", "block_number"]:
            if col not in df.columns:
                df[col] = None
        return df

    def _funding_source_signal(self, df: pd.DataFrame) -> dict:
        
        first_funders = {}
        df_sorted = df.sort_values("block_number")
        for _, row in df_sorted.iterrows():
            to_addr = row["to_address"]
            from_addr = row["from_address"]
            if pd.isna(to_addr) or pd.isna(from_addr):
                continue
            if to_addr not in first_funders:
                first_funders[to_addr] = from_addr

        groups = defaultdict(list)
        for wallet, funder in first_funders.items():
            groups[funder].append(wallet)

        return {funder: wallets for funder, wallets in groups.items() if len(wallets) >= 2}

    def _gas_fingerprint_signal(self, df: pd.DataFrame) -> dict:
        
        df_valid = df.dropna(subset=["from_address", "gas_price_gwei"])
        if df_valid.empty:
            return {}

        fingerprint = (
            df_valid.groupby("from_address")["gas_price_gwei"]
            .agg(lambda x: round(x.mode().iloc[0], 4) if not x.mode().empty else None)
            .dropna()
        )

        groups = defaultdict(list)
        for wallet, gas in fingerprint.items():
            groups[gas].append(wallet)

        return {gas: wallets for gas, wallets in groups.items() if len(wallets) >= 2}

    def _shared_counterparty_signal(self, df: pd.DataFrame) -> dict:
        
        df_valid = df.dropna(subset=["from_address", "to_address"])
        wallet_targets = df_valid.groupby("from_address")["to_address"].apply(set)

        groups = defaultdict(list)
        wallets = list(wallet_targets.index)
        for w1, w2 in combinations(wallets, 2):
            overlap = wallet_targets[w1] & wallet_targets[w2]
            if len(overlap) >= 2:  
                key = frozenset([w1, w2])
                groups[key] = list(key)

        return groups

    def run(self) -> list:
        df = self.load_data()
        if df.empty:
            logging.warning("No transaction data — skipping clustering")
            self._save([])
            return []

        funding_groups = self._funding_source_signal(df)
        gas_groups = self._gas_fingerprint_signal(df)
        counterparty_groups = self._shared_counterparty_signal(df)

        
        parent = {}

        def find(x):
            parent.setdefault(x, x)
            while parent[x] != x:
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        all_signals = []

        for funder, wallets in funding_groups.items():
            for w in wallets:
                union(w, wallets[0])
            all_signals.append(("common_funding_source", wallets, funder))

        for gas, wallets in gas_groups.items():
            for w in wallets:
                union(w, wallets[0])
            all_signals.append(("identical_gas_fingerprint", wallets, str(gas)))

        for key, wallets in counterparty_groups.items():
            for w in wallets:
                union(w, wallets[0])
            all_signals.append(("shared_counterparties", wallets, None))

        
        clusters = defaultdict(set)
        for wallet in parent:
            clusters[find(wallet)].add(wallet)

        result = []
        for cluster_id, (root, wallets) in enumerate(clusters.items()):
            if len(wallets) < 2:
                continue

            
            evidence = []
            for sig_type, sig_wallets, sig_meta in all_signals:
                if set(sig_wallets) & wallets:
                    evidence.append({"type": sig_type, "detail": str(sig_meta)})

            confidence = min(95, 40 + 20 * len(evidence))

            result.append({
                "cluster_id": f"CLUSTER-{cluster_id+1}",
                "wallets": list(wallets),
                "wallet_count": len(wallets),
                "confidence_score": confidence,
                "evidence": evidence,
                "label": self._guess_label(evidence),
            })

        result.sort(key=lambda x: x["confidence_score"], reverse=True)
        self._save(result)
        logging.info("Detected %d wallet clusters", len(result))
        return result

    def _guess_label(self, evidence: list) -> str:
        types = {e["type"] for e in evidence}
        if "identical_gas_fingerprint" in types and "shared_counterparties" in types:
            return "Likely Bot Network (scripted multi-wallet)"
        if "common_funding_source" in types:
            return "Likely Sybil Cluster (same funding origin)"
        if "shared_counterparties" in types:
            return "Coordinated Trading Group"
        return "Possible Related Wallets"

    def _save(self, result: list):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(result, f, indent=2, default=str)


if __name__ == "__main__":
    agent = WalletClusteringAgent()
    clusters = agent.run()
    print(json.dumps(clusters, indent=2, default=str))