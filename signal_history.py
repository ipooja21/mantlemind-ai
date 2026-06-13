import os
import csv
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SignalHistory] %(message)s")

DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "signal_history.csv")


def log_signal(alpha_score: float, signal: str):
    
    os.makedirs(DATA_DIR, exist_ok=True)
    file_exists = os.path.exists(HISTORY_FILE)

    with open(HISTORY_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "alpha_score", "signal"])
        writer.writerow([datetime.utcnow().isoformat(), round(float(alpha_score), 2), signal])

    logging.info("Logged signal: %.2f (%s)", alpha_score, signal)


def get_backtest_stats(window: int = 50) -> dict:
    
    if not os.path.exists(HISTORY_FILE):
        return {"accuracy": None, "sample_size": 0, "message": "No signal history yet."}

    rows = []
    with open(HISTORY_FILE, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if len(rows) < 2:
        return {"accuracy": None, "sample_size": 0, "message": "Not enough history yet — keep running scans."}

    rows = rows[-(window + 1):]  # need pairs, so +1

    correct = 0
    total = 0

    for i in range(len(rows) - 1):
        cur = rows[i]
        nxt = rows[i + 1]

        signal = cur["signal"].upper()
        cur_score = float(cur["alpha_score"])
        nxt_score = float(nxt["alpha_score"])

        if signal in ("NEUTRAL", "NEUTRA"):
            continue

        total += 1
        if "BULL" in signal and nxt_score > cur_score:
            correct += 1
        elif "BEAR" in signal and nxt_score < cur_score:
            correct += 1

    if total == 0:
        return {"accuracy": None, "sample_size": 0, "message": "No directional signals yet (all NEUTRAL)."}

    accuracy = round((correct / total) * 100, 1)
    return {
        "accuracy": accuracy,
        "sample_size": total,
        "message": f"Last {total} directional signals were {accuracy}% accurate.",
    }


if __name__ == "__main__":
    print(get_backtest_stats())