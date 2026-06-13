import streamlit as st


AGENTS = [
    {"id": 1,  "name": "Data Collector",     "icon": "⚡", "color": "#00C2B2"},
    {"id": 2,  "name": "Anomaly Detector",   "icon": "⚠️", "color": "#FF9800"},
    {"id": 3,  "name": "Whale Tracker",      "icon": "🐋", "color": "#0080FF"},
    {"id": 4,  "name": "Alpha Generator",    "icon": "📊", "color": "#7C4DFF"},
    {"id": 5,  "name": "Alert Dispatcher",   "icon": "🔔", "color": "#FF6B6B"},
    {"id": 6,  "name": "Report Builder",     "icon": "📄", "color": "#22d3ee"},
    {"id": 7,  "name": "LLM Synthesis",      "icon": "🧠", "color": "#f472b6"},
    {"id": 8,  "name": "Smart Watchlist",    "icon": "👁️", "color": "#a78bfa"},
    {"id": 9,  "name": "Entity Clustering",  "icon": "🕸️", "color": "#34d399"},
    {"id": 10, "name": "MEV Detector",       "icon": "🥪", "color": "#fbbf24"},
]


def inject_world_class_css():
    
    st.markdown(
        """
        <style>
        /* ── Respect reduced-motion preference ─────────────────── */
        @media (prefers-reduced-motion: reduce) {
            * { animation: none !important; transition: none !important; }
        }

        /* ── Agent Pulse Strip ───────────────────────────────────── */
        .pulse-strip {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding: 4px 0 12px 0;
            margin-bottom: 8px;
            scrollbar-width: thin;
        }
        .pulse-pill {
            position: relative;
            flex: 1 1 0;
            min-width: 86px;
            background: linear-gradient(135deg, #071428, #0A1E35);
            border: 1px solid #0E2A45;
            border-radius: 10px;
            padding: 8px 10px 7px 10px;
            text-align: center;
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
            cursor: default;
        }
        .pulse-pill:hover {
            transform: translateY(-3px);
            border-color: var(--pulse-color);
            box-shadow: 0 6px 18px -6px var(--pulse-color);
        }
        .pulse-dot {
            width: 7px; height: 7px; border-radius: 50%;
            background: var(--pulse-color);
            display: inline-block;
            margin-bottom: 4px;
            box-shadow: 0 0 0 0 var(--pulse-color);
            animation: pulseGlow 2.4s ease-out infinite;
        }
        @keyframes pulseGlow {
            0%   { box-shadow: 0 0 0 0 color-mix(in srgb, var(--pulse-color) 55%, transparent); }
            70%  { box-shadow: 0 0 0 6px transparent; }
            100% { box-shadow: 0 0 0 0 transparent; }
        }
        .pulse-icon { font-size: 15px; display: block; margin-bottom: 2px; }
        .pulse-id   { font-size: 9px; color: #5A7A9A; letter-spacing: 1px; font-family: 'JetBrains Mono', monospace; }
        .pulse-name { font-size: 10px; color: #B0C4DE; font-weight: 600; margin-top: 2px; line-height: 1.2; }

        /* ── Section fade-in on load ─────────────────────────────── */
        .fade-section {
            animation: fadeInUp 0.5s ease both;
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(8px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        /* ── Empty state ──────────────────────────────────────────── */
        .empty-state {
            display: flex; align-items: center; gap: 14px;
            background: rgba(10, 22, 40, 0.5);
            border: 1px dashed #1E3A5F;
            border-radius: 10px;
            padding: 16px 18px;
            margin: 6px 0;
        }
        .empty-state-icon { font-size: 22px; opacity: 0.8; }
        .empty-state-title { font-size: 13px; font-weight: 700; color: #B0C4DE; margin-bottom: 2px; }
        .empty-state-msg { font-size: 12px; color: #5A7A9A; }

        /* ── Visible keyboard focus ──────────────────────────────── */
        button:focus-visible, input:focus-visible, [role="slider"]:focus-visible {
            outline: 2px solid #00C2B2 !important;
            outline-offset: 2px !important;
        }

        /* ── Live badge ───────────────────────────────────────────── */
        .live-badge {
            display: inline-flex; align-items: center; gap: 6px;
            font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
            color: #00E676; text-transform: uppercase;
        }
        .live-badge .pulse-dot { --pulse-color: #00E676; margin-bottom: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_agent_pulse_strip(state: dict | None = None):
    
    status_text = {1: "live", 2: "scanning", 3: "scanning", 4: "computed",
                    5: "armed", 6: "ready", 7: "synthesised", 8: "watching",
                    9: "clustering", 10: "scanning"}

    if state:
        anom = state.get("anomaly_summary", {}).get("total_anomalies", 0)
        whales = len(state.get("whale_alerts", []))
        clusters = len(state.get("wallet_clusters", []))
        mev = len(state.get("mev_alerts", []))
        status_text[2] = f"{anom} flagged" if anom else "clean"
        status_text[3] = f"{whales} active" if whales else "quiet"
        status_text[9] = f"{clusters} clusters" if clusters else "clear"
        status_text[10] = f"{mev} found" if mev else "clean"

    html = ['<div class="pulse-strip">']
    for a in AGENTS:
        html.append(
            f'<div class="pulse-pill" style="--pulse-color:{a["color"]};">'
            f'<span class="pulse-dot"></span>'
            f'<span class="pulse-icon">{a["icon"]}</span>'
            f'<span class="pulse-id">AGENT {a["id"]:02d}</span>'
            f'<div class="pulse-name">{a["name"]}</div>'
            f'</div>'
        )
    html.append('</div>')
    st.markdown("".join(html), unsafe_allow_html=True)


def render_empty_state(icon: str, title: str, message: str):
    
    st.markdown(
        f"""
        <div class="empty-state">
            <div class="empty-state-icon">{icon}</div>
            <div>
                <div class="empty-state-title">{title}</div>
                <div class="empty-state-msg">{message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_live_badge(label: str = "LIVE · MANTLE MAINNET"):
    
    st.markdown(
        f'<span class="live-badge"><span class="pulse-dot"></span>{label}</span>',
        unsafe_allow_html=True,
    )