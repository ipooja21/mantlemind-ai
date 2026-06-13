import json
import os
import streamlit as st
import pandas as pd

try:
    import plotly.graph_objects as go
    import networkx as nx
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False



def render_reasoning_chain(alpha_score, signal, whale_count, anomaly_count, tx_count):
    st.markdown('<div class="section-header">🧠 AI REASONING CHAIN — HOW THE VERDICT WAS REACHED</div>', unsafe_allow_html=True)

    steps = [
        {
            "agent": "Agent 1",
            "title": "Data Collection",
            "detail": f"Scanned latest blocks → {tx_count} transactions ingested from Mantle Mainnet.",
            "color": "#22d3ee",
        },
        {
            "agent": "Agent 2",
            "title": "Anomaly Detection",
            "detail": f"Isolation Forest model flagged {anomaly_count} anomalous transaction(s).",
            "color": "#facc15" if anomaly_count > 0 else "#22c55e",
        },
        {
            "agent": "Agent 3",
            "title": "Whale Tracking",
            "detail": f"{whale_count} whale wallet(s) crossed the configured threshold.",
            "color": "#60a5fa",
        },
        {
            "agent": "Agent 4",
            "title": "Alpha Score Computation",
            "detail": (
                f"Combined Whale Signal, Volume Trend, Gas Momentum, Contract activity "
                f"and Anomaly Penalty → final score = {alpha_score:.1f}/100."
            ),
            "color": "#a78bfa",
        },
        {
            "agent": "Agent 7",
            "title": "LLM Synthesis",
            "detail": (
                f"Interpreted the composite score as a '{signal}' signal and generated "
                f"a natural-language market insight."
            ),
            "color": "#f472b6",
        },
    ]

    
    parts = ['<div style="border-left:2px solid #334155; margin-left:10px; padding-left:20px;">']

    for step in steps:
        parts.append(
            '<div style="position:relative; margin-bottom:18px;">'
            f'<div style="position:absolute; left:-31px; top:2px; width:14px; height:14px; '
            f'border-radius:50%; background:{step["color"]}; box-shadow:0 0 8px {step["color"]};"></div>'
            f'<div style="font-size:0.75rem; color:{step["color"]}; font-weight:700; letter-spacing:0.05em;">'
            f'{step["agent"]} · {step["title"]}</div>'
            f'<div style="font-size:0.9rem; color:#cbd5e1; margin-top:2px;">{step["detail"]}</div>'
            '</div>'
        )

    parts.append(
        '<div style="position:relative;">'
        '<div style="position:absolute; left:-31px; top:2px; width:14px; height:14px; '
        'border-radius:50%; background:#10b981; box-shadow:0 0 10px #10b981;"></div>'
        f'<div style="font-size:0.8rem; color:#10b981; font-weight:800;">'
        f'✅ FINAL VERDICT: {signal} (Alpha Score {alpha_score:.1f}/100)</div>'
        '</div>'
    )

    parts.append('</div>')
    chain_html = "".join(parts)

    st.markdown(chain_html, unsafe_allow_html=True)



def render_agent_voting(alpha_score, signal, whale_count, anomaly_count, components=None):
    st.markdown('<div class="section-header">🗳️ AGENT COUNCIL — MULTI-AGENT CONSENSUS</div>', unsafe_allow_html=True)

    components = components or {}
    whale_signal_score = components.get("whale_signal", 50.0)

    def _score_to_vote(score: float) -> str:
        if score >= 60:
            return "BULLISH"
        elif score <= 40:
            return "BEARISH"
        return "NEUTRAL"

    
    votes = []

    votes.append({
        "agent": "Agent 2 — Anomaly",
        "vote": "BEARISH" if anomaly_count > 0 else "NEUTRAL",
        "weight": 0.20,
        "reason": f"{anomaly_count} anomalies detected" if anomaly_count > 0 else "No anomalies",
    })

    if whale_count > 0:
        whale_vote = _score_to_vote(whale_signal_score)
        whale_reason = f"{whale_count} active whale wallet(s) — signal score {whale_signal_score:.0f}/100"
    else:
        whale_vote = "NEUTRAL"
        whale_reason = "No whale activity"

    votes.append({
        "agent": "Agent 3 — Whale",
        "vote": whale_vote,
        "weight": 0.25,
        "reason": whale_reason,
    })
    votes.append({
        "agent": "Agent 4 — Alpha Model",
        "vote": signal,
        "weight": 0.35,
        "reason": f"Composite alpha score = {alpha_score:.1f}/100",
    })
    votes.append({
        "agent": "Agent 7 — LLM Synthesis",
        "vote": signal,
        "weight": 0.20,
        "reason": "Natural-language interpretation of all signals",
    })

    color_map = {"BULLISH": "#22c55e", "BEARISH": "#ef4444", "NEUTRAL": "#94a3b8", "BEAR": "#ef4444", "BULL": "#22c55e"}

    cols = st.columns(len(votes))
    for col, v in zip(cols, votes):
        c = color_map.get(v["vote"].upper(), "#94a3b8")
        with col:
            st.markdown(
                f"""
                <div style="background:#0f172a; border:1px solid #1e293b; border-radius:10px;
                            padding:12px; text-align:center;">
                    <div style="font-size:0.7rem; color:#94a3b8; letter-spacing:0.05em; margin-bottom:6px;">
                        {v['agent']}
                    </div>
                    <div style="font-size:1.1rem; font-weight:800; color:{c};">
                        {v['vote']}
                    </div>
                    <div style="font-size:0.65rem; color:#64748b; margin-top:4px;">
                        weight {int(v['weight']*100)}%
                    </div>
                    <div style="font-size:0.7rem; color:#cbd5e1; margin-top:6px;">
                        {v['reason']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        f"""
        <div style="margin-top:10px; padding:10px; border-radius:8px; background:#0f172a;
                    border-left:4px solid {color_map.get(signal.upper(), '#94a3b8')};">
            <span style="color:#cbd5e1; font-size:0.85rem;">
            🏛️ <b>Council Decision:</b> Weighted consensus →
            <span style="color:{color_map.get(signal.upper(), '#94a3b8')}; font-weight:800;">{signal}</span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_wallet_clusters(json_path: str = "data/wallet_clusters.json"):
    st.markdown('<div class="section-header">🕸️ SMART MONEY ENTITY CLUSTERING — AGENT 9</div>', unsafe_allow_html=True)
    st.caption("Detects wallets likely controlled by the same actor (sybil farms, bot networks, coordinated trading).")

    if not os.path.exists(json_path):
        st.info("Run `agent9_wallet_clustering.py` to generate cluster data.")
        return

    with open(json_path, "r") as f:
        clusters = json.load(f)

    if not clusters:
        st.info("No multi-wallet clusters detected in current scan.")
        return

    for cluster in clusters[:5]:  # show top 5
        conf = cluster["confidence_score"]
        bar_color = "#ef4444" if conf >= 80 else "#facc15" if conf >= 60 else "#60a5fa"

        with st.expander(
            f"🔗 {cluster['cluster_id']} — {cluster['label']} "
            f"({cluster['wallet_count']} wallets, {conf}% confidence)"
        ):
            st.markdown(
                f"""
                <div style="background:#1e293b; border-radius:6px; height:8px; margin-bottom:10px;">
                    <div style="background:{bar_color}; width:{conf}%; height:8px; border-radius:6px;"></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("**Linked Wallets:**")
            for w in cluster["wallets"]:
                st.code(w, language=None)

            st.markdown("**Evidence:**")
            for ev in cluster["evidence"]:
                st.markdown(f"- `{ev['type']}` — {ev.get('detail', '')}")



def inject_glassmorphism_css():
    """Call this once near the top of app.py (after st.set_page_config)
    to give cards/metrics a glassmorphism look matching the existing
    dark theme."""
    st.markdown(
        """
        <style>
        [data-testid="stMetric"], div.element-container:has(> div > div[data-testid="stExpander"]) {
            background: rgba(15, 23, 42, 0.55);
            border: 1px solid rgba(56, 189, 248, 0.15);
            border-radius: 14px;
            padding: 4px 8px;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 28px rgba(34, 211, 238, 0.15);
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(15,23,42,0.95) 0%, rgba(2,6,23,0.95) 100%);
            border-right: 1px solid rgba(56, 189, 248, 0.1);
        }
        .stButton > button {
            border-radius: 10px;
            border: none;
            background: linear-gradient(90deg, #06b6d4, #3b82f6);
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            box-shadow: 0 0 16px rgba(34, 211, 238, 0.5);
            transform: translateY(-1px);
        }
        h1, h2, h3 {
            background: linear-gradient(90deg, #22d3ee, #818cf8);
            -webkit-background-clip: text;
            background-clip: text;
        }

        /* ── Sidebar widget dark-theme fixes ─────────────────── */
        [data-testid="stNumberInput"] input,
        [data-testid="stTextInput"] input,
        .stTextInput input {
            background: #0A1628 !important;
            color: #E2E8F0 !important;
            border: 1px solid #0E2A45 !important;
            border-radius: 6px !important;
        }
        [data-testid="stNumberInput"] button {
            background: #0A1628 !important;
            color: #00C2B2 !important;
            border: 1px solid #0E2A45 !important;
        }
        /* Slider track + thumb */
        div[data-baseweb="slider"] > div > div {
            background: #0E2A45 !important;
        }
        div[data-baseweb="slider"] [role="slider"] {
            background: #00C2B2 !important;
            box-shadow: 0 0 8px rgba(0, 194, 178, 0.6) !important;
        }
        /* Checkbox */
        [data-testid="stCheckbox"] label span {
            background: #0A1628 !important;
            border: 1px solid #0E2A45 !important;
        }
        /* select_slider labels */
        [data-baseweb="slider"] + div { color: #5A7A9A !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )



def render_predictive_accuracy(alpha_score, signal):
    """Shows 'Last N directional signals were X% accurate' using
    real historical data from data/signal_history.csv (see
    signal_history.py). Call log_signal() in your pipeline first."""
    try:
        from signal_history import get_backtest_stats
        stats = get_backtest_stats()
    except Exception:
        stats = {"accuracy": None, "sample_size": 0, "message": "Signal history module not found."}

    if stats["accuracy"] is None:
        st.caption(f"📈 {stats['message']}")
        return

    sample_size = stats["sample_size"]
    if sample_size < 5:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:10px; margin-top:6px;">
                <div style="font-size:0.85rem; color:#94a3b8;">📈 Predictive Track Record:</div>
                <div style="font-size:0.85rem; color:#60a5fa;">Building history… ({sample_size}/5 signals collected)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    acc = stats["accuracy"]
    color = "#22c55e" if acc >= 60 else "#facc15" if acc >= 45 else "#ef4444"

    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:10px; margin-top:6px;">
            <div style="font-size:0.85rem; color:#94a3b8;">📈 Predictive Track Record:</div>
            <div style="font-size:0.95rem; font-weight:800; color:{color};">{acc}% accurate</div>
            <div style="font-size:0.75rem; color:#64748b;">(last {sample_size} directional signals)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_mev_alerts(json_path: str = "data/mev_alerts.json"):
    st.markdown('<div class="section-header">🥪 MEV / SANDWICH ATTACK DETECTOR — AGENT 10</div>', unsafe_allow_html=True)
    st.caption("Detects front-run + back-run patterns around victim transactions within the same block.")

    if not os.path.exists(json_path):
        st.info("Run `agent10_mev_detector.py` to scan for sandwich attacks.")
        return

    with open(json_path, "r") as f:
        alerts = json.load(f)

    if not alerts:
        st.success("✅ No sandwich attack patterns detected in current scan.")
        return

    for alert in alerts[:5]:
        conf_color = "#ef4444" if alert["confidence"] == "HIGH" else "#facc15"
        st.markdown(
            f"""
            <div style="background:#1e1525; border:1px solid {conf_color}40; border-left:4px solid {conf_color};
                        border-radius:8px; padding:10px 14px; margin-bottom:8px;">
                <div style="font-size:0.85rem; color:#f1f5f9;">
                    🥪 Block <b>{alert['block_number']}</b> —
                    Attacker <code>{alert['attacker_wallet'][:10]}...</code> sandwiched
                    victim <code>{alert['victim_wallet'][:10]}...</code>
                    on contract <code>{alert['target_contract'][:10]}...</code>
                </div>
                <div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">
                    Front-run gas: {alert['attacker_gas_gwei']} gwei · Victim gas: {alert['victim_gas_gwei']} gwei ·
                    Confidence: <span style="color:{conf_color}; font-weight:700;">{alert['confidence']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )



def render_wallet_network_graph(tx_cache_path: str = "data/tx_cache.csv", max_edges: int = 60):
    st.markdown('<div class="section-header">🌐 LIVE WALLET INTERACTION NETWORK</div>', unsafe_allow_html=True)
    st.caption("Force-directed graph of wallet ↔ contract interactions from the current scan.")

    if not PLOTLY_AVAILABLE:
        st.warning("Install `plotly` and `networkx` to enable this view: `pip install plotly networkx`")
        return

    if not os.path.exists(tx_cache_path):
        st.info("No transaction data found.")
        return

    df = pd.read_csv(tx_cache_path)
    if df.empty or "from_address" not in df.columns or "to_address" not in df.columns:
        st.info("No transaction data found.")
        return

    df = df.dropna(subset=["from_address", "to_address"]).tail(max_edges)

    G = nx.Graph()
    for _, row in df.iterrows():
        G.add_edge(row["from_address"][:10] + "...", row["to_address"][:10] + "...",
                   weight=float(row.get("value_mnt", 0) or 0))

    if G.number_of_nodes() == 0:
        st.info("Not enough data to build a network graph.")
        return

    pos = nx.spring_layout(G, seed=42, k=0.6)

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1, color="rgba(56, 189, 248, 0.35)"),
        hoverinfo="none",
    )

    node_x, node_y, node_text, node_size, node_color = [], [], [], [], []
    has_hub = False
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        degree = G.degree(node)
        node_text.append(f"{node} · {degree} connections")
        node_size.append(10 + degree * 4)
        # contracts/hubs (relatively higher degree) get a different color
        if degree >= 2:
            node_color.append("#f472b6")
            has_hub = True
        else:
            node_color.append("#22d3ee")

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers",
        marker=dict(size=node_size, color=node_color, line=dict(width=1, color="#0f172a")),
        text=node_text, hoverinfo="text",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=420,
    )

    st.plotly_chart(fig, use_container_width=True)
    if has_hub:
        st.caption("🟣 Pink nodes = high-activity hubs (likely contracts/DEXs) · 🔵 Blue = regular wallets")
    else:
        st.caption("🔵 All wallets in this scan show low connectivity — no high-activity hubs detected yet.")