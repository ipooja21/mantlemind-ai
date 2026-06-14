# MantleMind AI

### Autonomous 10-Agent On-Chain Intelligence Platform for Mantle Network
### Turing Test Hackathon 2026 — Track: AI Alpha & Data

---

## Live Demo

[MantleMind AI Dashboard](https://mantlemind-ai-dxpfatlcdx4q2443be7cei.streamlit.app)

## Demo Video

[Watch on YouTube](https://youtu.be/KQnQyNUcG5w)

---

## What is MantleMind AI

MantleMind AI is a production-grade autonomous intelligence platform built natively on Mantle Network. It deploys 10 specialized AI agents that continuously monitor live blockchain activity, detect anomalies using machine learning, track whale movements, identify MEV attacks, and generate actionable market intelligence — with zero manual intervention required.

The platform was built to solve a real problem. Mantle blockchain data moves too fast for humans to monitor manually. Traders miss whale movements. Analysts miss anomaly spikes. Institutions have no automated risk monitoring for Mantle ecosystem. MantleMind AI fixes all of this with a fully autonomous multi-agent pipeline.


## 10 Agents — What Each One Does

**Agent 1 — Data Collector**
Connects directly to Mantle Mainnet RPC and ingests live blocks and transactions in real-time. Extracts wallet addresses, transaction values, gas prices, and contract interactions automatically on every scan.

**Agent 2 — Anomaly Detector**
Runs Isolation Forest machine learning model trained on live Mantle transaction data. Scores every transaction from 0 to 1 and classifies as LOW, MEDIUM, HIGH, or CRITICAL risk. Real ML — not rule-based filtering.

**Agent 3 — Whale Tracker**
Monitors MNT transfer volumes above configurable thresholds. Detects smart money accumulation and distribution patterns. Identifies whale behavior across multiple blocks to separate genuine whales from noise.

**Agent 4 — Alpha Signal Generator**
Combines five weighted signals into a single Alpha Score from 0 to 100. Signals: Whale Activity, Volume Trend, Gas Momentum, Contract Activity, and Anomaly Penalty. Outputs directional verdict: Strong Bull, Bull, Neutral, Bear, or Strong Bear. Tracks prediction accuracy across historical signals.

**Agent 5 — Alert Dispatcher**
Sends automated Telegram notifications every time anomalies are detected. Messages include anomaly rate, critical transaction count, and total detections. Full alert history logged with timestamps for complete audit trail.

**Agent 6 — Report Builder**
Generates investor-ready PDF reports and Excel files on demand. Reports include executive summary, network statistics, anomaly analysis, whale activity, alpha signal breakdown, and AI narrative. Designed for institutional use and quantitative analysis.

**Agent 7 — LLM Synthesis**
Integrates Groq API with LLaMA model to convert raw blockchain signals into natural language market insights. Explains the reasoning behind every signal in plain English. Generates unique insight text for every scan based on live data context.

**Agent 8 — Smart Watchlist**
Users add any Mantle wallet address to a personal watchlist. System monitors those wallets in every scan and triggers instant alerts when watched wallets become active on chain.

**Agent 9 — Entity Clustering**
Applies unsupervised clustering to detect wallets likely controlled by the same actor. Identifies sybil farms, bot networks, and coordinated trading groups. Outputs clusters with confidence scores and wallet counts.

**Agent 10 — MEV Detector**
Scans every block for sandwich attack patterns by detecting front-run and back-run transactions around victim transactions within the same block. First MEV detection system built specifically for Mantle Network.



## Live Results from Mainnet Testing

During live testing on Mantle Mainnet the system processed 25 transactions in under 7 seconds. Anomaly rates ranged from 8 percent to 45 percent across different block windows. Critical transactions were flagged and Telegram alerts dispatched automatically. PDF reports generated instantly. Wallet clusters detected with 60 percent confidence. MEV detector actively scanning every block in real-time.

## Built By

**Pooja Kumari**
Python Developer and AI/ML Engineer
B.Tech Computer Science
University of Engineering and Management, Jaipur

[GitHub](https://github.com/ipooja21) — [LinkedIn](https://linkedin.com/in/pooja-kumari-734b71284)

---

*MantleMind AI — Turing Test Hackathon 2026 — Built on Mantle Network*
